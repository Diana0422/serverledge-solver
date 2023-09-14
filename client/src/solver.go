package src

import (
	"client/config"
	pb "client/proto/github.com/grussorusso/serverledge"
	"context"
	"google.golang.org/grpc"
	"log"
)

func solve() {
	var opts []grpc.DialOption

	opts = append(opts, grpc.WithInsecure())

	serverAddr := config.GetString(config.SOLVER_ADDRESS, "localhost:2500")

	conn, err := grpc.Dial(serverAddr, opts...)
	defer conn.Close()
	if err != nil {
		log.Fatal(err)
	}

	client := pb.NewSolverClient(conn)

	response, err := client.Solve(context.Background(), &pb.Request{
		OffloadLatency: nil,
		Functions:      nil,
		Classes:        nil,
		Cost:           nil,
		Cpu:            nil,
		Memory:         nil,
	})

	if err != nil {
		log.Println(err)
	}

	response.GetFResponse()
}
