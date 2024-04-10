VERSION=v14
DOCKERUSER=owingit

build:
	docker build -f Dockerfile -t nst-rest .

push:
	docker tag nst-rest $(DOCKERUSER)/nst-rest:$(VERSION)
	docker push $(DOCKERUSER)/nst-rest:$(VERSION)
	docker tag nst-rest $(DOCKERUSER)/nst-rest:latest
	docker push $(DOCKERUSER)/nst-rest:latest
