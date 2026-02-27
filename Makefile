.PHONY: deploy teardown test lint

STACK_NAME := flare
REGION     ?= us-east-1

# Required
EMAIL          ?=
LOG_GROUP_PATTERNS ?=

# Triggers (all default to template defaults if not set)
ENABLE_SCHEDULE     ?=
SCHEDULE_EXPRESSION ?=
ENABLE_ALARM        ?=
ALARM_NAME_PREFIX   ?=
ENABLE_SUBSCRIPTION ?=
SUBSCRIPTION_LOG_GROUP ?=
SUBSCRIPTION_FILTER ?=

# Analysis
LOOKBACK_MINUTES ?=
TOKEN_BUDGET     ?=

# Voice (optional -- provisions Connect + Lex automatically)
CONNECT_ENABLED ?=
ONCALL_PHONE    ?=

define check_param
$(if $($(1)),,$(error $(1) is required. Usage: make deploy $(1)=<value>))
endef

# Build the --parameter-overrides string, only including params that are set
OVERRIDES := LogGroupPatterns=$(LOG_GROUP_PATTERNS) NotificationEmail=$(EMAIL)
ifneq ($(ENABLE_SCHEDULE),)
	OVERRIDES += EnableSchedule=$(ENABLE_SCHEDULE)
endif
ifneq ($(SCHEDULE_EXPRESSION),)
	OVERRIDES += ScheduleExpression="$(SCHEDULE_EXPRESSION)"
endif
ifneq ($(ENABLE_ALARM),)
	OVERRIDES += EnableAlarmTrigger=$(ENABLE_ALARM)
endif
ifneq ($(ALARM_NAME_PREFIX),)
	OVERRIDES += AlarmNamePrefix=$(ALARM_NAME_PREFIX)
endif
ifneq ($(ENABLE_SUBSCRIPTION),)
	OVERRIDES += EnableSubscription=$(ENABLE_SUBSCRIPTION)
endif
ifneq ($(SUBSCRIPTION_LOG_GROUP),)
	OVERRIDES += SubscriptionLogGroup=$(SUBSCRIPTION_LOG_GROUP)
endif
ifneq ($(SUBSCRIPTION_FILTER),)
	OVERRIDES += SubscriptionFilterPattern="$(SUBSCRIPTION_FILTER)"
endif
ifneq ($(LOOKBACK_MINUTES),)
	OVERRIDES += LookbackMinutes=$(LOOKBACK_MINUTES)
endif
ifneq ($(TOKEN_BUDGET),)
	OVERRIDES += TokenBudget=$(TOKEN_BUDGET)
endif
ifneq ($(CONNECT_ENABLED),)
	OVERRIDES += ConnectEnabled=$(CONNECT_ENABLED)
endif
ifneq ($(ONCALL_PHONE),)
	OVERRIDES += OncallPhone=$(ONCALL_PHONE)
endif

deploy:
	$(call check_param,EMAIL)
	$(call check_param,LOG_GROUP_PATTERNS)
	aws cloudformation deploy \
		--template-file template.yaml \
		--stack-name $(STACK_NAME) \
		--region $(REGION) \
		--capabilities CAPABILITY_IAM \
		--parameter-overrides $(OVERRIDES)
	@echo "Done. Check your email to confirm the SNS subscription."

teardown:
	aws cloudformation delete-stack --stack-name $(STACK_NAME) --region $(REGION)
	@echo "Stack deletion initiated (includes Connect instance and Lex bot if voice was enabled)."

test:
	pytest -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/flare/
