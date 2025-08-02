# MITMPROXY CAPTURE TOOL - Simplified & Elegant
# Quick workflow: make run → browse normally → make stop → make view

# Configuration - Load from config file
PYTHON := $(shell if [ -f venv/bin/python ]; then echo "venv/bin/python"; else echo "python3"; fi)
OUTPUT_DIR := $(shell $(PYTHON) -c "from config import config; print(config.output_dir)")
VIEWER_PORT := $(shell $(PYTHON) -c "from config import config; print(config.viewer_port)")
CAPTURE_FILE := $(OUTPUT_DIR)/capture_$(shell date +%Y%m%d_%H%M%S).mitm
LAST_CAPTURE := $(OUTPUT_DIR)/.last_capture
PID_FILE := $(OUTPUT_DIR)/.mitmtool.pid

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m

.PHONY: help run stop status view clean basic timeline docs viewer open-timeline config request

# Default target - show elegant help
help:
	@echo "$(BLUE)🕵️  MITMPROXY CAPTURE TOOL$(NC)"
	@echo ""
	@echo "$(GREEN)Simple workflow:$(NC)"
	@echo "  $(YELLOW)make run$(NC)      → Start proxy & capture everything"
	@echo "  $(YELLOW)make stop$(NC)     → Stop capture (auto-organizes)"
	@echo "  $(YELLOW)make view$(NC)     → Browse organized results"
	@echo ""
	@echo "$(GREEN)✨ Enhanced features (NEW!):$(NC)"
	@echo "  $(YELLOW)make timeline$(NC) → Generate timeline from existing capture"
	@echo "  $(YELLOW)make docs$(NC)     → Generate API docs from existing capture"
	@echo "  $(YELLOW)make viewer$(NC)   → 🚀 Open interactive API docs in browser"
	@echo "  $(YELLOW)make open-timeline$(NC) → 🕒 Open timeline in browser"
	@echo "  $(YELLOW)make basic$(NC)    → Run in basic mode (no enhancements)"
	@echo ""
	@echo "$(GREEN)Other commands:$(NC)"
	@echo "  $(YELLOW)make request <dir>$(NC) → Test API call from specific directory"
	@echo "  $(YELLOW)make config$(NC)   → Show current configuration"
	@echo "  $(YELLOW)make status$(NC)   → Check current status"
	@echo "  $(YELLOW)make clean$(NC)    → Remove all files"
	@echo ""
	@echo "$(BLUE)💡 Quick start: Run '$(YELLOW)make run$(NC)$(BLUE)', browse normally, then '$(YELLOW)make stop$(NC)$(BLUE)'$(NC)"
	@echo "$(BLUE)🚀 NEW: Enhanced mode includes API docs + timeline + ads blocking!$(NC)"
	@echo "$(BLUE)📚 Full documentation: $(YELLOW)cat addons.md$(NC)"

# Show current configuration
config:
	@echo "$(BLUE)⚙️  Current Configuration:$(NC)"
	@echo "  $(YELLOW)Output Directory:$(NC) $(OUTPUT_DIR)"
	@echo "  $(YELLOW)Viewer Port:$(NC) $(VIEWER_PORT)"
	@echo ""
	@echo "$(BLUE)💡 Edit .env file to change settings$(NC)"

# Main command - start everything at once
run:
	@echo "$(BLUE)🚀 Starting mitmproxy capture session...$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "$(YELLOW)⚠️  Session already running (PID: $$PID)$(NC)"; \
			echo "$(BLUE)💡 Use 'make stop' to end current session$(NC)"; \
			exit 1; \
		else \
			rm -f $(PID_FILE); \
		fi; \
	fi
	@echo "$(YELLOW)📡 Enabling proxy & starting capture...$(NC)"
	@echo "$(YELLOW)📁 File: $(CAPTURE_FILE)$(NC)"
	@echo "$(GREEN)✨ Browse normally - all traffic will be captured$(NC)"
	@echo "$(GREEN)🔗 Install certificate: http://mitm.it$(NC)"
	@echo "$(BLUE)💡 Run 'make stop' when finished$(NC)"
	@echo ""
	@echo "$(CAPTURE_FILE)" > $(LAST_CAPTURE)
	@$(PYTHON) mitmtool.py run --output $(CAPTURE_FILE) > $(OUTPUT_DIR)/capture.log 2>&1 & echo $$! > $(PID_FILE)
	@sleep 2
	@if [ -f $(PID_FILE) ] && ps -p $$(cat $(PID_FILE)) > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Session started successfully$(NC)"; \
		echo "$(BLUE)📊 Proxy active on http://127.0.0.1:8080$(NC)"; \
	else \
		echo "$(RED)❌ Failed to start session$(NC)"; \
		if [ -f $(OUTPUT_DIR)/capture.log ]; then tail -3 $(OUTPUT_DIR)/capture.log; fi; \
		rm -f $(PID_FILE); \
		exit 1; \
	fi

# Stop and organize everything
stop:
	@echo "$(BLUE)🛑 Stopping capture session...$(NC)"
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "$(YELLOW)🔄 Stopping capture...$(NC)"; \
			kill $$PID 2>/dev/null || true; \
			sleep 2; \
			if ps -p $$PID > /dev/null 2>&1; then kill -9 $$PID 2>/dev/null || true; fi; \
		fi; \
		rm -f $(PID_FILE); \
	fi
	@$(PYTHON) mitmtool.py stop > /dev/null 2>&1 || true
	@if [ -f $(LAST_CAPTURE) ]; then \
		CAPTURE=$$(cat $(LAST_CAPTURE)); \
		if [ -f "$$CAPTURE" ]; then \
			echo "$(YELLOW)📚 Generating enhanced reports...$(NC)"; \
			$(PYTHON) generate_reports.py "$$CAPTURE" "$(OUTPUT_DIR)"; \
			if [ $$? -eq 0 ]; then \
				echo "$(GREEN)🎉 Session complete! All reports generated$(NC)"; \
				echo "$(BLUE)🚀 API Docs: $(OUTPUT_DIR)/api_docs/viewer.html$(NC)"; \
				echo "$(BLUE)🕒 Timeline: $(OUTPUT_DIR)/api_timeline/timeline.html$(NC)"; \
				echo "$(BLUE)📡 Network Traffic: $(OUTPUT_DIR)/<domain>/<call_dirs>/$(NC)"; \
				echo "$(BLUE)💡 Run 'make viewer' to open interactive docs$(NC)"; \
			else \
				echo "$(YELLOW)⚠️  Enhanced reports failed$(NC)"; \
			fi; \
		else \
			echo "$(YELLOW)⚠️  No capture file found$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  No active session found$(NC)"; \
	fi

# Check current status
status:
	@echo "$(BLUE)🔍 Current status:$(NC)"
	@$(PYTHON) mitmtool.py status
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "$(GREEN)🟢 Capture session active (PID: $$PID)$(NC)"; \
			echo "$(BLUE)📁 File: $$(cat $(LAST_CAPTURE) 2>/dev/null || echo 'unknown')$(NC)"; \
		else \
			echo "$(RED)🔴 No active capture session$(NC)"; \
			rm -f $(PID_FILE); \
		fi; \
	else \
		echo "$(YELLOW)📴 No capture session running$(NC)"; \
	fi

# View organized results
view:
	@if [ -d "$(OUTPUT_DIR)" ]; then \
		echo "$(BLUE)📂 Network Traffic Results: $(OUTPUT_DIR)$(NC)"; \
		echo ""; \
		DOMAIN_COUNT=$$(find "$(OUTPUT_DIR)" -mindepth 1 -maxdepth 1 -type d ! -name "api_docs" ! -name "api_timeline" | wc -l | tr -d ' '); \
		if [ $$DOMAIN_COUNT -gt 0 ]; then \
			CALL_COUNT=$$(find "$(OUTPUT_DIR)" -name "request.json" -type f | wc -l | tr -d ' '); \
			echo "$(GREEN)Found $$CALL_COUNT API calls across $$DOMAIN_COUNT domains:$(NC)"; \
			echo ""; \
			find "$(OUTPUT_DIR)" -mindepth 1 -maxdepth 1 -type d ! -name "api_docs" ! -name "api_timeline" | head -5 | while read domain_dir; do \
				domain=$$(basename "$$domain_dir"); \
				call_count=$$(find "$$domain_dir" -name "request.json" -type f | wc -l | tr -d ' '); \
				echo "  $(YELLOW)$$domain$(NC): $$call_count calls"; \
				find "$$domain_dir" -mindepth 1 -maxdepth 1 -type d | head -3 | while read call_dir; do \
					call_name=$$(basename "$$call_dir"); \
					echo "    • $$call_name"; \
				done; \
			done; \
			if [ $$DOMAIN_COUNT -gt 5 ]; then echo "  $(BLUE)... and $$(($$DOMAIN_COUNT - 5)) more domains$(NC)"; fi; \
			echo ""; \
			echo "$(BLUE)💡 Browse: cd $(OUTPUT_DIR)/<domain>/<call_dir>$(NC)"; \
			echo "$(BLUE)💡 View request: cat request.json$(NC)"; \
			echo "$(BLUE)💡 Test request: make request $(OUTPUT_DIR)/<domain>/<call_dir>$(NC)"; \
			echo "$(BLUE)💡 Check auth: cat auth.txt$(NC)"; \
			echo "$(BLUE)💡 View metadata: cat metadata.json$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  No traffic recordings found$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  No results yet. Run 'make run' then 'make stop' first$(NC)"; \
	fi

# Clean up everything
clean:
	@echo "$(BLUE)🧹 Cleaning up all files...$(NC)"
	@if [ -f $(PID_FILE) ]; then \
		echo "$(YELLOW)🛑 Stopping active session first...$(NC)"; \
		$(MAKE) stop; \
	fi
	@rm -rf $(OUTPUT_DIR)
	@rm -rf *.pyc __pycache__ .DS_Store
	@echo "$(GREEN)✅ All files removed$(NC)"

# Run in basic mode (no enhanced features)
basic:
	@echo "$(BLUE)🔧 Starting basic capture session (enhanced features disabled)...$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "$(YELLOW)⚠️  Session already running (PID: $$PID)$(NC)"; \
			exit 1; \
		else \
			rm -f $(PID_FILE); \
		fi; \
	fi
	@echo "$(CAPTURE_FILE)" > $(LAST_CAPTURE)
	@$(PYTHON) mitmtool.py run --basic --output $(CAPTURE_FILE) > $(OUTPUT_DIR)/capture.log 2>&1 & echo $$! > $(PID_FILE)
	@sleep 2
	@if [ -f $(PID_FILE) ] && ps -p $$(cat $(PID_FILE)) > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Basic session started$(NC)"; \
	else \
		echo "$(RED)❌ Failed to start session$(NC)"; \
		rm -f $(PID_FILE); \
		exit 1; \
	fi

# Generate enhanced reports from existing capture
timeline:
	@if [ -f $(LAST_CAPTURE) ]; then \
		CAPTURE=$$(cat $(LAST_CAPTURE)); \
		if [ -f "$$CAPTURE" ]; then \
			echo "$(BLUE)🕒 Generating timeline from $$CAPTURE...$(NC)"; \
			$(PYTHON) generate_reports.py "$$CAPTURE" "$(OUTPUT_DIR)"; \
			if [ $$? -eq 0 ]; then \
				echo "$(GREEN)✅ Timeline generated: $(OUTPUT_DIR)/api_timeline/timeline.html$(NC)"; \
				echo "$(BLUE)💡 Open in browser to view chronological API calls$(NC)"; \
			fi; \
		else \
			echo "$(RED)❌ Capture file not found: $$CAPTURE$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  No recent capture found. Specify file: python generate_reports.py your_file.mitm $(OUTPUT_DIR)$(NC)"; \
	fi

# Generate API docs (alias for timeline)
docs: timeline

# Open API documentation viewer in browser
viewer:
	@if [ -d "$(OUTPUT_DIR)/api_docs" ]; then \
		echo "$(BLUE)🚀 Starting API documentation server...$(NC)"; \
		echo "$(GREEN)💡 This will open your browser automatically$(NC)"; \
		echo "$(GREEN)📚 Press Ctrl+C to stop the server when done$(NC)"; \
		$(PYTHON) serve_docs.py $(OUTPUT_DIR)/api_docs -p $(VIEWER_PORT); \
	else \
		echo "$(YELLOW)⚠️  No API docs found. Run 'make run' then 'make stop' first.$(NC)"; \
	fi

# Open timeline in browser
open-timeline:
	@if [ -f "$(OUTPUT_DIR)/api_timeline/timeline.html" ]; then \
		echo "$(BLUE)🕒 Opening API timeline...$(NC)"; \
		open $(OUTPUT_DIR)/api_timeline/timeline.html; \
	else \
		echo "$(YELLOW)⚠️  No timeline found. Run 'make run' then 'make stop' first.$(NC)"; \
	fi

# Test API request from a specific directory
request:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "$(YELLOW)⚠️  Usage: make request <directory_path>$(NC)"; \
		echo "$(BLUE)💡 Example: make request $(OUTPUT_DIR)/airdna.com/post_submarkets_2024-08-02_14-30-15_001$(NC)"; \
		exit 1; \
	fi
	@DIR="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ ! -d "$$DIR" ]; then \
		echo "$(RED)❌ Directory not found: $$DIR$(NC)"; \
		exit 1; \
	fi; \
	if [ ! -f "$$DIR/request.json" ]; then \
		echo "$(RED)❌ No request.json found in: $$DIR$(NC)"; \
		exit 1; \
	fi; \
	echo "$(BLUE)🚀 Testing API request from: $$DIR$(NC)"; \
	if [ -f venv/bin/activate ]; then \
		cd "$$DIR" && source ../../../venv/bin/activate && python ../../../test_request.py .; \
	else \
		cd "$$DIR" && python3 ../../../test_request.py .; \
	fi

# Prevent make from treating directory arguments as targets
%:
	@:
