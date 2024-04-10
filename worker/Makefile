USER=owingit
VERSION=v29
current-dir := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

build:
	docker build -f Dockerfile -t nst-worker .
push:
	docker tag nst-worker $(USER)/nst-worker:$(VERSION)
	docker push $(USER)/nst-worker:$(VERSION)
	docker tag nst-worker $(USER)/nst-worker:latest
	docker push $(USER)/nst-worker:latest
