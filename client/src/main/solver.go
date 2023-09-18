package main

import (
	"client/src/config"
	"client/src/node"
	pb "client/src/proto/github.com/grussorusso/serverledge"
	"context"
	"fmt"
	"google.golang.org/grpc"
	"log"
)

const (
	LOCAL           = 0
	OFFLOADED_CLOUD = 1
	OFFLOADED_EDGE  = 2
)

type classFunctionInfo struct {
	*functionInfo //Pointer used for accessing information about the function
	//
	probExecuteLocal float64
	probOffloadCloud float64
	probOffloadEdge  float64
	probDrop         float64
	//
	arrivals     float64
	arrivalCount float64
	//
	share float64
	//
	timeSlotsWithoutArrivals int
	//
	className string
}

/*
*

	 	Stores the function information and metrics.
		Metrics are stored as an array with size 3, to maintain also horizontal offloading data
*/
type functionInfo struct {
	name             string
	count            [3]int64   //Number of function requests
	meanDuration     [3]float64 //Mean duration time
	varianceDuration [3]float64 //Variance of the duration time
	coldStartCount   [3]int64   //Count the number of cold starts to estimate probCold
	timeSlotCount    [3]int64   //Count the number of calls in the time slot
	missed           int        //Number of requests that missed the deadline TODO maybe remove
	initTime         [3]float64 //Average of init times when cold start
	memory           int64      //Memory requested by the function
	cpu              float64    //CPU requested by the function
	probCold         [3]float64 //Probability of a cold start when requesting the function

	//Map containing information about function requests for every class
	invokingClasses map[string]*classFunctionInfo
}

var CloudOffloadLatency = 0.0
var EdgeOffloadLatency = 0.0

func solve(m map[string]*functionInfo) {
	if len(m) == 0 {
		return
	}

	var opts []grpc.DialOption

	opts = append(opts, grpc.WithInsecure())

	serverAddr := config.GetString(config.SOLVER_ADDRESS, "localhost:2500")

	conn, err := grpc.Dial(serverAddr, opts...)
	defer conn.Close()
	if err != nil {
		log.Fatal(err)
	}

	client := pb.NewSolverClient(conn)

	functionList := make([]*pb.Function, 0)

	//TODO do only once
	classList := make([]*pb.QosClass, 0)

	for _, fInfo := range m {
		invocationList := make([]*pb.FunctionInvocation, 0)

		for _, cFInfo := range fInfo.invokingClasses {
			arrivals := float32(cFInfo.arrivals)

			invocationList = append(invocationList, &pb.FunctionInvocation{
				QosClass: &cFInfo.className,
				Arrivals: &arrivals,
			})
		}

		memory := int32(fInfo.memory)
		cpu := float32(fInfo.cpu)
		name := fInfo.name
		durationLocal := float32(fInfo.meanDuration[LOCAL])
		durationOffloadedCloud := float32(fInfo.meanDuration[OFFLOADED_CLOUD])
		durationOffloadedEdge := float32(fInfo.meanDuration[OFFLOADED_EDGE])
		initTimeLocal := float32(fInfo.initTime[LOCAL])
		initTimeOffloadedCloud := float32(fInfo.initTime[OFFLOADED_CLOUD])
		initTimeOffloadedEdge := float32(fInfo.initTime[OFFLOADED_EDGE])
		pCold := float32(fInfo.probCold[LOCAL])
		pColdOffloadedCloud := float32(fInfo.probCold[OFFLOADED_CLOUD])
		pColdOffloadedEdge := float32(fInfo.probCold[OFFLOADED_EDGE])

		x := &pb.Function{
			Name:                   &name,
			Memory:                 &memory,
			Cpu:                    &cpu,
			Invocations:            invocationList,
			Duration:               &durationLocal,
			DurationOffloadedCloud: &durationOffloadedCloud,
			DurationOffloadedEdge:  &durationOffloadedEdge,
			InitTime:               &initTimeLocal,
			InitTimeOffloadedCloud: &initTimeOffloadedCloud,
			InitTimeOffloadedEdge:  &initTimeOffloadedEdge,
			Pcold:                  &pCold,
			PcoldOffloadedCloud:    &pColdOffloadedCloud,
			PcoldOffloadedEdge:     &pColdOffloadedEdge,
		}

		functionList = append(functionList, x)
	}

	if len(classList) == 0 {
		for cName, class := range Classes {
			utility := float32(class.Utility)
			mrt := float32(class.MaximumResponseTime)
			completedPercentage := float32(class.CompletedPercentage)
			name := cName

			classList = append(classList, &pb.QosClass{
				Name:                &name,
				Utility:             &utility,
				MaxResponseTime:     &mrt,
				CompletedPercentage: &completedPercentage,
			})
		}
	}

	offloadLatencyCloud := float32(CloudOffloadLatency)
	offloadLatencyEdge := float32(EdgeOffloadLatency)
	costCloud := float32(config.GetFloat(config.CLOUD_COST, 0.01))
	localCpu := float32(node.Resources.MaxCPUs)
	localMem := float32(node.Resources.MaxMemMB)
	response, err := client.Solve(context.Background(), &pb.Request{
		OffloadLatencyCloud: &offloadLatencyCloud,
		OffloadLatencyEdge:  &offloadLatencyEdge,
		Functions:           functionList,
		Classes:             classList,
		CostCloud:           &costCloud,
		CpuLocal:            &localCpu,
		MemoryLocal:         &localMem,
	})

	if err != nil {
		log.Println(err)
	}

	log.Println("Evaluation took: ", response.GetTimeTaken())
	res := response.GetFResponse()

	for _, r := range res {
		fInfo, prs := m[r.GetName()]

		if !prs {
			log.Println("Error in assigning probabilities")
			continue
		}

		invokingClasses := fInfo.invokingClasses
		for _, x := range r.GetClassResponses() {
			cFInfo, prs := invokingClasses[x.GetName()]
			if !prs {
				log.Println("Error in assigning probabilities")
				continue
			}

			cFInfo.probExecuteLocal = float64(x.GetPL())
			cFInfo.probOffloadCloud = float64(x.GetPC())
			cFInfo.probOffloadEdge = float64(x.GetPE())
			cFInfo.probDrop = float64(x.GetPD())
			cFInfo.share = float64(x.GetShare())
		}
	}

}

/*func solve() {
	var opts []grpc.DialOption

	opts = append(opts, grpc.WithInsecure())

	serverAddr := "localhost:2500"
	fmt.Println(serverAddr)

	conn, err := grpc.Dial(serverAddr, opts...)
	defer conn.Close()
	if err != nil {
		log.Fatal(err)
	}

	client := pb.NewSolverClient(conn)

	var fInfo functionInfo
	var cInfo classFunctionInfo

	arrivals := float32(cInfo.arrivals)

	cInfo = classFunctionInfo{
		functionInfo:             nil,
		probExecute:              0,
		probOffload:              0,
		probDrop:                 0,
		arrivals:                 0,
		arrivalCount:             0,
		share:                    0,
		timeSlotsWithoutArrivals: 0,
		className:                "Bella Class",
	}

	fInfo = functionInfo{
		name:             "Bella function",
		count:            [2]int64{4, 4},
		meanDuration:     [2]float64{3.5, 5.5},
		varianceDuration: [2]float64{2.3, 1.2},
		coldStartCount:   [2]int64{3, 1},
		timeSlotCount:    [2]int64{5, 5},
		missed:           0,
		initTime:         [2]float64{1.0, 0.5},
		memory:           100,
		cpu:              10,
		probCold:         [2]float64{0.5, 0.5},
		invokingClasses: map[string]*classFunctionInfo{
			"class1": &cInfo,
		},
	}

	functionList := make([]*pb.Function, 0)
	classList := make([]*pb.QosClass, 0)
	invocationList := make([]*pb.FunctionInvocation, 0)

	invocationList = append(invocationList, &pb.FunctionInvocation{
		QosClass: &cInfo.className,
		Arrivals: &arrivals,
	})

	memory := int32(fInfo.memory)
	cpu := float32(fInfo.cpu)
	name := fInfo.name
	durationLocal := float32(fInfo.meanDuration[LOCAL])
	durationOffloaded := float32(fInfo.meanDuration[OFFLOADED])
	initTimeLocal := float32(fInfo.initTime[LOCAL])
	initTimeOffloaded := float32(fInfo.initTime[OFFLOADED])
	pcold := float32(fInfo.probCold[LOCAL])
	pcoldOffloaded := float32(fInfo.probCold[OFFLOADED])

	x := &pb.Function{
		Name:                   &name,
		Memory:                 &memory,
		Cpu:                    &cpu,
		Invocations:            invocationList,
		Duration:               &durationLocal,
		DurationOffloadedCloud: &durationOffloaded,
		DurationOffloadedEdge:  &durationOffloaded,
		InitTime:               &initTimeLocal,
		InitTimeOffloadedCloud: &initTimeOffloaded,
		InitTimeOffloadedEdge:  &initTimeOffloaded,
		Pcold:                  &pcold,
		PcoldOffloadedCloud:    &pcoldOffloaded,
		PcoldOffloadedEdge:     &pcoldOffloaded,
	}

	functionList = append(functionList, x)
	latency := float32(OffloadLatency)
	cost := float32(CloudCost)
	cpu = float32(maxCPU)
	mem := float32(maxMemMB)
	response, err := client.Solve(context.Background(), &pb.Request{
		OffloadLatency: &latency,
		Functions:      functionList,
		Classes:        classList,
		Cost:           &cost,
		Cpu:            &cpu,
		Memory:         &mem,
	})

	if err != nil {
		log.Println(err)
	}

	log.Println("Evaluation took: ", response.GetTimeTaken())
	res := response.GetFResponse()
	log.Println(res)
}*/

func main() {
	fmt.Println("Let's go requesting!")
	cInfo := classFunctionInfo{
		functionInfo:             nil,
		probExecuteLocal:         0.25,
		probOffloadCloud:         0.25,
		probOffloadEdge:          0.25,
		probDrop:                 0.25,
		arrivals:                 7,
		arrivalCount:             7,
		share:                    0,
		timeSlotsWithoutArrivals: 0,
		className:                "default",
	}

	classes := make(map[string]*classFunctionInfo)
	classes["default"] = &cInfo

	fInfo := functionInfo{
		name:             "func",
		count:            [3]int64{4, 3, 1},
		meanDuration:     [3]float64{0.9, 2.2, 1.0},
		varianceDuration: [3]float64{0.0, 0.0, 0.0},
		coldStartCount:   [3]int64{2, 1, 0},
		timeSlotCount:    [3]int64{1, 1, 1},
		missed:           0,
		initTime:         [3]float64{0.05, 0.003, 0.0},
		memory:           2049,
		cpu:              10,
		probCold:         [3]float64{0.33, 0.33, 0.33},
		invokingClasses:  classes,
	}

	m := make(map[string]*functionInfo)
	m["func"] = &fInfo
	addDefaultClass()
	solve(m)
}
