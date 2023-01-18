
REGISTRY = "gcr.io/on-prem-test-314219/interview-project"

all:
	docker build --platform linux/amd64 -t webapp webapp
	docker tag webapp:latest ${REGISTRY}/webapp:latest
	docker push ${REGISTRY}/webapp:latest

