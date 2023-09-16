package src

import (
	"client/src/config"
	"log"
	"testing"
)

func TestRegistration(t *testing.T) {

	region := config.GetString(config.REGISTRY_AREA, "PIPPO")
	registry := &Registry{Area: "lb/" + region}

	if _, err := registry.RegisterToEtcd("localhost:2379"); err != nil {
		log.Printf("Could not register to Etcd: %v", err)
	}
}

func TestGetCloudNodes(t *testing.T) {
	region, err := GetCloudNodes("ROME")
	for key, element := range region {
		log.Println("Key:", key, "=>", "Element:", element)
	}
	if err != nil {
		log.Println("Could not recover cloud nodes")
	}

}

func TestRegistry_GetAll(t *testing.T) {
	region := config.GetString(config.REGISTRY_AREA, "ROME")
	registry := &Registry{Area: "" + region}

	result, err := registry.GetAll(false)
	for key, element := range result {
		log.Println("Key:", key, "=>", "Element:", element)
	}

	if err != nil {
		log.Println("Could not recover other nodes infos")
	}
}
