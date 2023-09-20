package scheduling

import (
	"client/src/client"
	"client/src/config"
	"client/src/function"
	"client/src/node"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"time"
)

const (
	LOCAL     = 0
	OFFLOADED = 1
)

const (
	DROP_REQUEST    = 0
	EXECUTE_REQUEST = 1
	OFFLOAD_REQUEST = 2
)

var startingExecuteProb = 0.5 //0.0
var startingOffloadProb = 0.5 //1.0

var evaluationInterval time.Duration

var OffloadLatency = 0.0

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

var rGen *rand.Rand

var arrivalChannel = make(chan arrivalRequest, 1000)
var requestChannel = make(chan completedRequest, 1000)

// TODO add to config
var maxTimeSlots = 20

type completedRequest struct {
	*scheduledRequest
	location int
	dropped  bool
}

type arrivalRequest struct {
	*scheduledRequest
	class string
}

// TODO remove
func (fInfo *functionInfo) getProbCold(location int) float64 {
	if fInfo.timeSlotCount[location] == 0 {
		//If there are no arrivals there's a high probability that the function execution requires a cold start
		return 1
	} else {
		return float64(fInfo.coldStartCount[location]) / float64(fInfo.timeSlotCount[location])
	}
}

func canExecute(function *function.Function) bool {
	nContainers, _ := node.WarmStatus()[function.Name]
	if nContainers >= 1 {
		return true
	}

	if node.Resources.AvailableCPUs >= function.CPUDemand &&
		node.Resources.AvailableMemMB >= function.MemoryMB {
		return true
	}

	return false
}

// FIXME: dummy
func pickEdgeNodeForOffloading(r *scheduledRequest) string {
	return ""
}
func recoverRemoteUrl(r *scheduledRequest, isCloudUrl bool) string {
	if isCloudUrl {
		return config.GetString(config.CLOUD_URL, "")
	} else {
		// pick the edge node used for offloading and recover its url
		return pickEdgeNodeForOffloading(r)
	}
}

func calculatePacketSize(r *scheduledRequest, isCloudCalc bool) int {
	serverUrl := recoverRemoteUrl(r, isCloudCalc)
	request := client.InvocationRequest{Params: r.Params,
		QoSMaxRespT: r.MaxRespT,
		Async:       r.Async}
	invocationBody, err := json.Marshal(request)
	if err != nil {
		log.Print(err)
	}

	// Calculate approximate packet size
	sizePacket := len("POST /invoke/"+r.Fun.Name+" HTTP/1.1") +
		len("Host: "+serverUrl) +
		len("User-Agent: Go-http-client/1.1") +
		len("Content-Length: "+fmt.Sprintf("%d", len(invocationBody))) +
		len("Content-Type: application/json") +
		len("\r\n\r\n") +
		len(invocationBody)
	log.Println("size packet calculated")
	return sizePacket
}

type decisionEngine interface {
	InitDecisionEngine()
	updateProbabilities()
	Completed(r *scheduledRequest, offloaded int)
	Decide(r *scheduledRequest) int
	Delete(function string, class string)
}
