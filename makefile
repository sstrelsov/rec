# MITMPROXY API CAPTURE MAKEFILE
# Usage:
#   make start    - Enable proxy and start capturing
#   make stop     - Stop capture, disable proxy, organize APIs
#   make status   - Check proxy status
#   make clean    - Clean up all capture files
#   make view     - View last capture in organized format

# Configuration
CAPTURE_FILE := capture_$(shell date +%Y%m%d_%H%M%S).mitm
LAST_CAPTURE := .last_capture
API_DIR := api_calls_$(shell date +%Y%m%d_%H%M%S)
PID_FILE := .mitmdump.pid
PYTHON := python3

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

.PHONY: help start stop status clean view install check logs organize

# Default target
help:
	@echo "$(BLUE)🕵️  MITMPROXY API CAPTURE$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@echo "  $(YELLOW)make start$(NC)     - Enable proxy and start capturing traffic"
	@echo "  $(YELLOW)make stop$(NC)      - Stop capture, disable proxy, organize APIs"
	@echo "  $(YELLOW)make status$(NC)    - Check current proxy status"
	@echo "  $(YELLOW)make view$(NC)      - View last organized capture"
	@echo "  $(YELLOW)make clean$(NC)     - Clean up all capture files"
	@echo "  $(YELLOW)make install$(NC)   - Check/install dependencies"
	@echo "  $(YELLOW)make logs$(NC)      - View capture logs"
	@echo ""
	@echo "$(GREEN)Quick workflow:$(NC)"
	@echo "  1. $(YELLOW)make start$(NC)   # Start capturing"
	@echo "  2. Use your browser normally"
	@echo "  3. $(YELLOW)make stop$(NC)    # Stop and organize APIs"
	@echo "  4. $(YELLOW)make view$(NC)    # Browse organized results"

# Check if required tools are installed
check:
	@echo "$(BLUE)🔍 Checking dependencies...$(NC)"
	@command -v mitmdump >/dev/null 2>&1 || { echo "$(RED)❌ mitmproxy not found. Run 'make install'$(NC)"; exit 1; }
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "$(RED)❌ Python 3 not found$(NC)"; exit 1; }
	@[ -f mitmtool.py ] || { echo "$(RED)❌ mitmtool.py not found in current directory$(NC)"; exit 1; }
	@[ -f organize_api_calls.py ] || { echo "$(RED)❌ organize_api_calls.py not found$(NC)"; exit 1; }
	@echo "$(GREEN)✅ All dependencies found$(NC)"

# Install dependencies
install:
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	@if command -v brew >/dev/null 2>&1; then \
		echo "$(YELLOW)Installing mitmproxy via Homebrew...$(NC)"; \
		brew install mitmproxy; \
	else \
		echo "$(YELLOW)Installing mitmproxy via pip...$(NC)"; \
		pip3 install mitmproxy; \
	fi
	@echo "$(GREEN)✅ Dependencies installed$(NC)"
	@echo "$(YELLOW)💡 Don't forget to install the mitmproxy certificate:$(NC)"
	@echo "   1. Run 'make start'"
	@echo "   2. Visit http://mitm.it in your browser"
	@echo "   3. Download and install the certificate"

# Start proxy and capture
start: check
	@echo "$(BLUE)🚀 Starting mitmproxy capture...$(NC)"
	@if [ -f $(PID_FILE) ]; then \
		echo "$(YELLOW)⚠️  Capture already running (PID: $$(cat $(PID_FILE)))$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📡 Enabling proxy...$(NC)"
	@$(PYTHON) mitmtool.py enable
	@echo "$(YELLOW)🎬 Starting capture: $(CAPTURE_FILE)$(NC)"
	@echo "$(GREEN)💡 Use your browser normally. Press 'make stop' when done.$(NC)"
	@echo "$(GREEN)🔗 Install certificate: http://mitm.it$(NC)"
	@echo ""
	@echo "$(CAPTURE_FILE)" > $(LAST_CAPTURE)
	@nohup mitmdump -w $(CAPTURE_FILE) --listen-port 8080 > capture.log 2>&1 & echo $$! > $(PID_FILE)
	@sleep 2
	@if ps -p $$(cat $(PID_FILE)) > /dev/null; then \
		echo "$(GREEN)✅ Capture started successfully (PID: $$(cat $(PID_FILE)))$(NC)"; \
		echo "$(BLUE)📊 Monitoring traffic on http://127.0.0.1:8080$(NC)"; \
	else \
		echo "$(RED)❌ Failed to start capture$(NC)"; \
		rm -f $(PID_FILE); \
		exit 1; \
	fi

# Stop capture and organize
stop:
	@echo "$(BLUE)🛑 Stopping mitmproxy capture...$(NC)"
	@if [ ! -f $(PID_FILE) ]; then \
		echo "$(YELLOW)⚠️  No capture running$(NC)"; \
	else \
		echo "$(YELLOW)🔄 Stopping capture process...$(NC)"; \
		kill $$(cat $(PID_FILE)) 2>/dev/null || true; \
		sleep 3; \
		rm -f $(PID_FILE); \
		echo "$(GREEN)✅ Capture stopped$(NC)"; \
	fi
	@echo "$(YELLOW)📡 Disabling proxy...$(NC)"
	@$(PYTHON) mitmtool.py disable
	@if [ -f $(LAST_CAPTURE) ]; then \
		CAPTURE=$$(cat $(LAST_CAPTURE)); \
		if [ -f "$$CAPTURE" ]; then \
			echo "$(YELLOW)🗂️  Organizing APIs from $$CAPTURE...$(NC)"; \
			$(PYTHON) organize_api_calls.py "$$CAPTURE" $(API_DIR); \
			echo "$(GREEN)✅ APIs organized in: $(API_DIR)$(NC)"; \
			echo "$(API_DIR)" > .last_organized; \
			echo "$(BLUE)💡 Run 'make view' to browse organized APIs$(NC)"; \
		else \
			echo "$(RED)❌ Capture file not found: $$CAPTURE$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  No recent capture found$(NC)"; \
	fi

# Check proxy status
status:
	@echo "$(BLUE)🔍 Checking status...$(NC)"
	@$(PYTHON) mitmtool.py status
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null; then \
			echo "$(GREEN)✅ Capture running (PID: $$PID)$(NC)"; \
			echo "$(BLUE)📁 Current file: $$(cat $(LAST_CAPTURE) 2>/dev/null || echo 'unknown')$(NC)"; \
		else \
			echo "$(RED)❌ Capture process not found$(NC)"; \
			rm -f $(PID_FILE); \
		fi; \
	else \
		echo "$(YELLOW)📴 No capture running$(NC)"; \
	fi

# View organized APIs
view:
	@if [ -f .last_organized ]; then \
		API_DIR=$(cat .last_organized); \
		if [ -d "$API_DIR" ]; then \
			echo "$(BLUE)📂 Browsing organized APIs: $API_DIR$(NC)"; \
			echo ""; \
			find "$API_DIR" -name "request" -type f | head -20 | while read file; do \
				dir=$(dirname "$file"); \
				response_file=$(ls "$dir"/response* 2>/dev/null | head -1); \
				echo "$(GREEN)🔗 $dir$(NC)"; \
				echo "   Request: $file"; \
				echo "   Response: $response_file"; \
				echo ""; \
			done; \
			echo "$(YELLOW)💡 Usage examples:$(NC)"; \
			echo "   cd $API_DIR"; \
			echo "   ./api.github.com/get_users_octocat/request"; \
			echo "   cat api.github.com/get_users_octocat/response.json"; \
			echo "   open api.github.com/get_page/response.html"; \
		else \
			echo "$(RED)❌ Organized directory not found: $API_DIR$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  No organized APIs found. Run 'make stop' first.$(NC)"; \
	fi

# View capture logs
logs:
	@if [ -f capture.log ]; then \
		echo "$(BLUE)📋 Recent capture logs:$(NC)"; \
		tail -20 capture.log; \
	else \
		echo "$(YELLOW)⚠️  No logs found$(NC)"; \
	fi

# Organize existing capture file
organize:
	@if [ -f $(LAST_CAPTURE) ]; then \
		CAPTURE=$$(cat $(LAST_CAPTURE)); \
		if [ -f "$$CAPTURE" ]; then \
			echo "$(YELLOW)🗂️  Re-organizing $$CAPTURE...$(NC)"; \
			$(PYTHON) organize_api_calls.py "$$CAPTURE" $(API_DIR); \
			echo "$(GREEN)✅ APIs organized in: $(API_DIR)$(NC)"; \
			echo "$(API_DIR)" > .last_organized; \
		else \
			echo "$(RED)❌ No capture file found$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  No recent capture found$(NC)"; \
	fi

# Clean up files
clean:
	@echo "$(BLUE)🧹 Cleaning up...$(NC)"
	@if [ -f $(PID_FILE) ]; then \
		echo "$(YELLOW)⚠️  Stopping running capture first...$(NC)"; \
		make stop; \
	fi
	@echo "$(YELLOW)🗑️  Removing capture files...$(NC)"
	@rm -f *.mitm capture.log $(LAST_CAPTURE) $(PID_FILE) .last_organized
	@echo "$(YELLOW)🗑️  Removing organized API directories...$(NC)"
	@rm -rf api_calls_* api_calls/
	@echo "$(YELLOW)🗑️  Removing any leftover temp files...$(NC)"
	@rm -f *.pyc __pycache__/ .DS_Store
	@echo "$(GREEN)✅ Cleanup complete - all capture files and API directories removed$(NC)"

# Emergency stop - force kill everything
emergency-stop:
	@echo "$(RED)🚨 Emergency stop - killing all mitmproxy processes$(NC)"
	@sudo pkill -f mitm || true
	@rm -f $(PID_FILE)
	@$(PYTHON) mitmtool.py disable
	@echo "$(GREEN)✅ Emergency stop complete$(NC)"

# Show current files
ls:
	@echo "$(BLUE)📁 Current files:$(NC)"
	@echo "$(YELLOW)Capture files:$(NC)"
	@ls -la *.mitm 2>/dev/null || echo "  No capture files"
	@echo "$(YELLOW)Organized APIs:$(NC)"
	@ls -la api_calls_* 2>/dev/null || echo "  No organized directories"
	@echo "$(YELLOW)Status files:$(NC)"
	@ls -la .last_* $(PID_FILE) 2>/dev/null || echo "  No status files"
