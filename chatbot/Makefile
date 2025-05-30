include .env
export $(shell sed 's/=.*//' .env)

run:
	uvicorn src.main:app --reload

test-main:
	python3 ./src/main.py

install:
	pip3 install -r requirements.txt

start-docker:
	open -a Docker

check-aws-keys:
	@echo $(AWS_KEY)
	@echo $(AWS_SECRET_KEY)

deploy-prod:
	AWS_ACCESS_KEY_ID=$(AWS_KEY) AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_KEY) \
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 440209552728.dkr.ecr.us-east-1.amazonaws.com
	docker build -t voice-agent/turbo-journey .
	docker tag voice-agent/turbo-journey:latest 440209552728.dkr.ecr.us-east-1.amazonaws.com/voice-agent/turbo-journey:latest
	docker push 440209552728.dkr.ecr.us-east-1.amazonaws.com/voice-agent/turbo-journey:latest
	@echo "Image pushed successfully!"
	AWS_ACCESS_KEY_ID=$(AWS_KEY) AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_KEY) \
	aws ecs update-service --cluster turbo-journey-cluster --service turbo-journey-task-service-93rgynxv --force-new-deployment --region us-east-1 --no-cli-pager
	# @echo "ECS service updated successfully!