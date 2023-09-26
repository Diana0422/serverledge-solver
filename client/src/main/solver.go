package main

import (
	"client/src/config"
	"client/src/function"
	"client/src/node"
	pb "client/src/proto/github.com/grussorusso/serverledge"
	"client/src/registration"
	"context"
	"fmt"
	"github.com/LK4D4/trylock"
	"google.golang.org/grpc"
	"log"
	"math"
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
	packetSize       int        //Size of the function packet to send to possible host

	//Map containing information about function requests for every class
	invokingClasses map[string]*classFunctionInfo
}

var CloudOffloadLatency = 0.0
var EdgeOffloadLatency = 0.0

// Calculates the aggregated total memory of nearby nodes
func calculateAggregatedMem() float32 {
	aggrMem := float32(0)
	nearbyServerMap := registration.Reg.NearbyServersMap
	for key := range nearbyServerMap {
		info := nearbyServerMap[key]
		aggrMem += float32(info.AvailableMemMB)
	}
	return aggrMem
}

// calculateUsableMemoryCoefficient calculates the coefficient that explains if the local node has memory available to
// execute the function. It's calculated using the loss percentage of the local node.
func calculateUsableMemoryCoefficient() float64 {
	localRequests := node.Resources.RequestsCount
	blockedRequests := node.Resources.DropRequestsCount
	loss := 0.0
	coefficient := 1.1

	if localRequests > 0 {
		loss = float64(float32(blockedRequests) / float32(localRequests))
	} else {
		loss = 0
	}

	if loss > 0.0 {
		coefficient -= coefficient * loss / 2.0
	} else {
		coefficient = math.Min(coefficient*1.1, 1.0)
	}
	return coefficient
}

/*func solve(m map[string]*functionInfo) {
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

	aggregatedEdgeMemory := calculateAggregatedMem()
	// log.Println("aggregatedEdgeMemory: ", aggregatedEdgeMemory)
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
		MemoryLocal:         &localMem,
		CpuLocal:            &localCpu,
		MemoryAggregate:     &aggregatedEdgeMemory,
	})

	if err != nil {
		log.Println(err)
	}

	log.Println("Evaluation took: ", response.GetTimeTaken())
	res := response.GetFResponse()
	log.Println("Response: ", res)

	for _, r := range res {
		log.Println("r: ", r)
		log.Println("r.GetName: ", r.GetName())
		log.Println(m)
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
			log.Println("probExecuteLocal: ", cFInfo.probExecuteLocal)
			log.Println("probOffloadCloud: ", cFInfo.probOffloadCloud)
			log.Println("probOffloadEdge: ", cFInfo.probOffloadEdge)
			log.Println("probDrop: ", cFInfo.probDrop)
			log.Println("share: ", cFInfo.share)
		}
	}

}*/

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
		bandwidthCloud := float32(config.GetFloat(config.BANDWIDTH_CLOUD, 1.0))
		bandwidthEdge := float32(config.GetFloat(config.BANDWIDTH_EDGE, 1.0))

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
			BandwidthCloud:         &bandwidthCloud,
			BandwidthEdge:          &bandwidthEdge,
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

	aggregatedEdgeMemory := calculateAggregatedMem()
	offloadLatencyCloud := float32(CloudOffloadLatency)
	offloadLatencyEdge := float32(EdgeOffloadLatency)
	costCloud := float32(config.GetFloat(config.CLOUD_COST, 0.01))
	localBudget := float32(config.GetFloat(config.BUDGET, 0.01))
	localCpu := float32(node.Resources.MaxCPUs)
	localMem := float32(node.Resources.MaxMemMB)
	localUsableMem := float32(calculateUsableMemoryCoefficient())
	response, err := client.Solve(context.Background(), &pb.Request{
		OffloadLatencyCloud:     &offloadLatencyCloud,
		OffloadLatencyEdge:      &offloadLatencyEdge,
		Functions:               functionList,
		Classes:                 classList,
		CostCloud:               &costCloud,
		LocalBudget:             &localBudget,
		MemoryLocal:             &localMem,
		CpuLocal:                &localCpu,
		MemoryAggregate:         &aggregatedEdgeMemory,
		UsableMemoryCoefficient: &localUsableMem,
	})

	if err != nil {
		log.Println(err)
	}

	log.Println("Evaluation took: ", response.GetTimeTaken())
	res := response.GetFResponse()
	log.Println("Response: ", res)

	for _, r := range res {
		log.Println("r: ", r)
		log.Println("r.GetName: ", r.GetName())
		log.Println(m)
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
			log.Println("probExecuteLocal: ", cFInfo.probExecuteLocal)
			log.Println("probOffloadCloud: ", cFInfo.probOffloadCloud)
			log.Println("probOffloadEdge: ", cFInfo.probOffloadEdge)
			log.Println("probDrop: ", cFInfo.probDrop)
			log.Println("share: ", cFInfo.share)
		}
	}

}

func main() {
	// dummy registration
	registration.Reg = &registration.Registry{
		Area:             "",
		Key:              "",
		Client:           nil,
		RwMtx:            trylock.Mutex{},
		NearbyServersMap: make(map[string]*registration.StatusInformation),
		CloudServersMap:  nil,
	}
	infoNode1 := registration.StatusInformation{
		AvailableMemMB: 2048,
	}

	infoNode2 := registration.StatusInformation{
		AvailableMemMB: 2048,
	}
	registration.Reg.NearbyServersMap["node1"] = &infoNode1
	registration.Reg.NearbyServersMap["node2"] = &infoNode2

	fmt.Println("Let's go requesting!")
	cInfo := classFunctionInfo{
		functionInfo:             nil,
		probExecuteLocal:         0.3,
		probOffloadCloud:         0.3,
		probOffloadEdge:          0.3,
		probDrop:                 0.1,
		arrivals:                 0.09090909,
		arrivalCount:             0,
		share:                    0,
		timeSlotsWithoutArrivals: 0,
		className:                "default",
	}

	classes := make(map[string]*classFunctionInfo)
	classes["default"] = &cInfo

	fInfo := functionInfo{
		name:             "func",
		count:            [3]int64{1, 0, 0},
		meanDuration:     [3]float64{0.0, 0.0, 0.0045800372},
		varianceDuration: [3]float64{0.0, 0.0, 0.0},
		initTime:         [3]float64{0.0, 0.0, 0.77583396},
		memory:           600,
		cpu:              0,
		probCold:         [3]float64{0.0, 0.0, 1.0},
		invokingClasses:  classes,
	}

	m := make(map[string]*functionInfo)
	m["func"] = &fInfo
	cl := function.QoSClass{
		Name:                "default",
		Utility:             1,
		MaximumResponseTime: -1,
		CompletedPercentage: 0,
	}
	Classes["default"] = cl

	CloudOffloadLatency = 0.0
	EdgeOffloadLatency = 0.0011971339999999886
	solve(m)
}
