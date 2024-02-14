METAL_DEPLOYMENT_BASE_VERSION := latest

.PHONY: test-local
test-local:
	docker pull metalstack/metal-deployment-base:latest
	docker run --rm -it -v $(PWD):/work -w /work metalstack/metal-deployment-base:latest make test

.PHONY: test
test:
	python3 -m pip install mock metal_python
	./test.sh

.PHONY: run-test-example
run-test-example:
	docker run --rm -it \
		-v $(PWD):/metal-modules:ro \
		-w /metal-modules \
		--network host \
		ghcr.io/metal-stack/metal-deployment-base:$(METAL_DEPLOYMENT_BASE_VERSION) /bin/bash -ce \
		  "ansible-galaxy install --ignore-errors -r example-requirements.yaml && ansible-playbook example.yaml -v"
