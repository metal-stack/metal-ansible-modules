METAL_DEPLOYMENT_BASE_VERSION := v0.0.6

.PHONY: run-test-example
run-test-example:
	docker run --rm -it \
		-v $(PWD):/metal-modules:ro \
		-w /metal-modules \
		--network host \
		metalstack/metal-deployment-base:$(METAL_DEPLOYMENT_BASE_VERSION) /bin/bash -ce \
		  "ansible-galaxy install  --ignore-errors -r example-requirements.yaml && ansible-playbook example.yaml -v"
