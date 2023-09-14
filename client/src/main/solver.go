package main

import (
	pb "client/proto/github.com/grussorusso/serverledge"
	"context"
	"fmt"
	"google.golang.org/grpc"
	"log"
)

const (
	LOCAL     = 0
	OFFLOADED = 1
)

type classFunctionInfo struct {
	//Pointer used for accessing information about the function
	*functionInfo
	//
	probExecute float64
	probOffload float64
	probDrop    float64
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

type functionInfo struct {
	name string
	//Number of function requests
	count [2]int64
	//Mean duration time
	meanDuration [2]float64
	//Variance of the duration time
	varianceDuration [2]float64
	//Count the number of cold starts to estimate probCold
	coldStartCount [2]int64
	//Count the number of calls in the time slot
	timeSlotCount [2]int64
	//TODO maybe remove
	//Number of requests that missed the deadline
	missed int
	//Average of init times when cold start
	initTime [2]float64
	//Memory requested by the function
	memory int64
	//CPU requested by the function
	cpu float64
	//Probability of a cold start when requesting the function
	probCold [2]float64
	//Map containing information about function requests for every class
	invokingClasses map[string]*classFunctionInfo
}

var OffloadLatency = 0.0
var CloudCost = 0.01
var maxCPU = 100
var maxMemMB = 500

func solve() {
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
}

func main() {
	fmt.Println("Let's go requesting!")
	solve()
}
