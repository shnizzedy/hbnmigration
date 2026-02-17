.PHONY: version status check-ready-to-release release

# Read VERSION file
VERSION := $(shell cat VERSION 2>/dev/null | tr -d '[:space:]')

# Extract base version (remove -dev suffix) - uses shell parameter expansion
VERSION_BASE := $(shell v="$(VERSION)"; echo "$${v%-dev}")

# Get latest tag (remove 'v' prefix)
LATEST_TAG := $(shell git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0")

TAG := v$(VERSION_BASE)

# Show version status
status:
	@echo "================================"
	@echo "Version Status"
	@echo "================================"
	@echo "VERSION file:    $(VERSION)"
	@echo "Latest git tag:  $(LATEST_TAG)"
	@echo ""
	@if [ "$(VERSION_BASE)" = "$(LATEST_TAG)" ]; then \
		case "$(VERSION)" in \
			*-dev) \
				echo "Status: ⚠️  Development version matches released tag"; \
				echo "Action: 🔖 Bump to next version"; \
				;; \
			*) \
				echo "Status: ✅ At release (VERSION matches tag)"; \
				echo "Action: 🔖 Tag this commit or bump to next dev version"; \
				;; \
		esac \
	elif [ "$(VERSION_BASE)" \> "$(LATEST_TAG)" ]; then \
		echo "Status: 📝 Development in progress"; \
		echo "Action: 💻 Continue developing or prepare release"; \
	else \
		echo "Status: ❌ ERROR - VERSION behind tag!"; \
	fi
	@echo "================================"

# Check if ready to release
check-ready-to-release:
	@case "$(VERSION)" in \
		*-dev) \
			echo "❌ VERSION contains -dev suffix: $(VERSION)"; \
			echo "Remove -dev before releasing:"; \
			echo "  echo '$(VERSION_BASE)' > VERSION"; \
			exit 1; \
			;; \
	esac
	@if [ "$(VERSION_BASE)" = "$(LATEST_TAG)" ]; then \
		echo "❌ VERSION $(VERSION) already released (tag v$(LATEST_TAG) exists)"; \
		echo "Bump version first:"; \
		echo "  echo 'X.Y.Z' > VERSION"; \
		exit 1; \
	fi
	@if git rev-parse "$(TAG)" >/dev/null 2>&1; then \
		echo "❌ Tag $(TAG) already exists"; \
		exit 1; \
	fi
	@echo "✅ Ready to release version $(VERSION)"

# Create release
release: check-ready-to-release
	@echo "Creating release $(TAG)..."
	@git tag -a "$(TAG)" -m "Release $(TAG)"
	@echo "✅ Created tag: $(TAG)"
	@echo ""
	@echo "Push with:"
	@echo "  git push origin main --follow-tags"
	@echo ""
	@echo "After pushing, bump to next dev version:"
	@echo "  echo 'X.Y.Z-dev' > VERSION"
