/**
 * Discord Spammer Bot Tool
 * 
 * Frontend control for the Discord bot service running on the Data Ingestion Service.
 * Handles config loading, bot start/stop, and status polling.
 */

window.DiscordBot = {
  state: {
    zone: null,
    poi: null,
    channelId: null,
    botState: "idle",
  },

  configs: {
    zones: {},
    pois: {},
    channels: {},
  },

  statusPollInterval: null,
  statusPollMs: 10000, // Poll every 10 seconds

  /**
   * Initialize the tool - attach event listeners
   */
  init() {
    const reloadBtn = document.getElementById("discord_reload_btn");
    const startBtn = document.getElementById("discord_start_btn");
    const stopBtn = document.getElementById("discord_stop_btn");
    const zoneSelect = document.getElementById("discord_zone_select");
    const poiSelect = document.getElementById("discord_poi_select");
    const channelSelect = document.getElementById("discord_channel_select");

    reloadBtn?.addEventListener("click", () => this.handleReloadConfigs());
    startBtn?.addEventListener("click", () => this.handleStart());
    stopBtn?.addEventListener("click", () => this.handleStop());

    zoneSelect?.addEventListener("change", () => this.handleZoneChange());
    poiSelect?.addEventListener("change", () => this.handlePoiChange());
    channelSelect?.addEventListener("change", () => this.handleChannelChange());

    // Restore from localStorage if available
    this.restoreState();

    // Load configs on init
    this.loadConfigs();

    // Start polling for status
    this.startStatusPolling();
  },

  /**
   * Restore state from localStorage
   */
  restoreState() {
    const saved = localStorage.getItem("discord_bot_state");
    if (saved) {
      try {
        this.state = JSON.parse(saved);
      } catch (e) {
        console.warn("Failed to restore saved state:", e);
      }
    }
  },

  /**
   * Save current state to localStorage
   */
  saveState() {
    try {
      localStorage.setItem("discord_bot_state", JSON.stringify(this.state));
    } catch (e) {
      console.warn("Failed to save state to localStorage:", e);
    }
  },

  /**
   * Load configurations from backend
   */
  async loadConfigs() {
    try {
      const response = await fetch("/api/tools/discord_bot/configs");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.configs.zones = data.zones || {};
      this.configs.pois = data.pois || {};
      this.configs.channels = data.channels || {};

      this.populateSelects();
      this.showMessage("Configurations loaded", "success");
    } catch (error) {
      console.error("Failed to load configs:", error);
      this.showMessage(`Failed to load configs: ${error.message}`, "error");
    }
  },

  /**
   * Handle Reload Configs button
   */
  async handleReloadConfigs() {
    await this.loadConfigs();
  },

  /**
   * Populate dropdown selects with loaded configs
   */
  populateSelects() {
    const zoneSelect = document.getElementById("discord_zone_select");
    const poiSelect = document.getElementById("discord_poi_select");
    const channelSelect = document.getElementById("discord_channel_select");

    // Populate zones
    const zoneOptions = Object.keys(this.configs.zones).map(
      (zone) => `<option value="${zone}">${zone}</option>`
    );
    zoneSelect.innerHTML =
      '<option value="">-- Select a zone --</option>' + zoneOptions.join("");

    // Populate POIs
    const poiOptions = Object.keys(this.configs.pois).map(
      (poi) => `<option value="${poi}">${poi}</option>`
    );
    poiSelect.innerHTML =
      '<option value="">-- Select a POI --</option>' + poiOptions.join("");

    // Populate channels
    const channelOptions = Object.entries(this.configs.channels).map(
      ([name, id]) => `<option value="${id}">${name} (${id})</option>`
    );
    channelSelect.innerHTML =
      '<option value="">-- Select a channel --</option>' +
      channelOptions.join("");

    // Restore selections if available
    if (this.state.zone) zoneSelect.value = this.state.zone;
    if (this.state.poi) poiSelect.value = this.state.poi;
    if (this.state.channelId) channelSelect.value = this.state.channelId;

    // Enable selects only when configs are loaded
    zoneSelect.disabled = Object.keys(this.configs.zones).length === 0;
    poiSelect.disabled = Object.keys(this.configs.pois).length === 0;
    channelSelect.disabled = Object.keys(this.configs.channels).length === 0;
  },

  /**
   * Handle zone selection change
   */
  handleZoneChange() {
    this.state.zone = document.getElementById("discord_zone_select").value;
    this.saveState();
    this.updateUIState();
  },

  /**
   * Handle POI selection change
   */
  handlePoiChange() {
    this.state.poi = document.getElementById("discord_poi_select").value;
    this.saveState();
    this.updateUIState();
  },

  /**
   * Handle channel selection change
   */
  handleChannelChange() {
    const value = document.getElementById("discord_channel_select").value;
    this.state.channelId = value ? parseInt(value) : null;
    this.saveState();
    this.updateUIState();
  },

  /**
   * Handle Start Bot button
   */
  async handleStart() {
    if (!this.state.zone || !this.state.poi || !this.state.channelId) {
      this.showMessage("Please select a zone, POI, and channel", "error");
      return;
    }

    try {
      this.setUILoading(true);
      const response = await fetch("/api/tools/discord_bot/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          zone: this.state.zone,
          poi: this.state.poi,
          channel_id: this.state.channelId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const data = await response.json();
      this.state.botState = data.state;
      this.saveState();
      this.updateStatusBadge(data);
      this.showMessage(
        `Bot started for ${this.state.zone} / ${this.state.poi}`,
        "success"
      );
    } catch (error) {
      console.error("Failed to start bot:", error);
      this.showMessage(`Failed to start bot: ${error.message}`, "error");
    } finally {
      this.setUILoading(false);
    }
  },

  /**
   * Handle Stop Bot button
   */
  async handleStop() {
    try {
      this.setUILoading(true);
      const response = await fetch("/api/tools/discord_bot/stop", {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const data = await response.json();
      this.state.botState = data.state;
      this.state.zone = null;
      this.state.poi = null;
      this.state.channelId = null;
      this.saveState();
      this.updateStatusBadge(data);
      this.showMessage("Bot stopped", "success");
    } catch (error) {
      console.error("Failed to stop bot:", error);
      this.showMessage(`Failed to stop bot: ${error.message}`, "error");
    } finally {
      this.setUILoading(false);
    }
  },

  /**
   * Poll for bot status periodically
   */
  startStatusPolling() {
    // Poll immediately
    this.pollStatus();

    // Set up periodic polling
    this.statusPollInterval = setInterval(() => this.pollStatus(), this.statusPollMs);
  },

  /**
   * Poll for current bot status
   */
  async pollStatus() {
    try {
      const response = await fetch("/api/tools/discord_bot/status");
      if (!response.ok) {
        console.error(`Status poll failed: HTTP ${response.status}`);
        return;
      }

      const data = await response.json();
      this.state.botState = data.state;
      this.updateStatusBadge(data);
      this.updateUIState();
    } catch (error) {
      console.error("Status poll error:", error);
    }
  },

  /**
   * Update the status badge
   */
  updateStatusBadge(statusData) {
    const badge = document.getElementById("discord_status_badge");
    const errorMsg = document.getElementById("discord_error_message");

    if (!badge) return;

    const state = statusData.state || "idle";
    let statusText = "Offline";
    let statusClass = "idle";

    switch (state) {
      case "running":
        statusText = statusData.discord_connected ? "Running" : "Connecting...";
        statusClass = statusData.discord_connected ? "running" : "starting";
        break;
      case "starting":
        statusText = "Starting...";
        statusClass = "starting";
        break;
      case "stopping":
        statusText = "Stopping...";
        statusClass = "stopping";
        break;
      case "error":
        statusText = "Error";
        statusClass = "error";
        break;
      case "idle":
      default:
        statusText = "Offline";
        statusClass = "idle";
    }

    badge.dataset.state = statusClass;
    badge.querySelector(".status-text").textContent = statusText;

    // Show/hide error message
    if (state === "error" && statusData.error_msg) {
      errorMsg.textContent = `Error: ${statusData.error_msg}`;
      errorMsg.style.display = "block";
    } else {
      errorMsg.style.display = "none";
    }

    // Update info section
    if (state === "running") {
      document.getElementById("discord_info_section").style.display = "block";
      document.getElementById("discord_info_zone").textContent = statusData.zone;
      document.getElementById("discord_info_poi").textContent = statusData.poi;
      document.getElementById("discord_info_channel").textContent =
        statusData.channel_id;
    } else {
      document.getElementById("discord_info_section").style.display = "none";
    }
  },

  /**
   * Update UI button states based on current bot state
   */
  updateUIState() {
    const startBtn = document.getElementById("discord_start_btn");
    const stopBtn = document.getElementById("discord_stop_btn");
    const zoneSelect = document.getElementById("discord_zone_select");
    const poiSelect = document.getElementById("discord_poi_select");
    const channelSelect = document.getElementById("discord_channel_select");

    const isRunning = this.state.botState === "running";
    const isTransitioning =
      this.state.botState === "starting" || this.state.botState === "stopping";

    // Enable/disable buttons based on state
    startBtn.disabled =
      isRunning ||
      isTransitioning ||
      !this.state.zone ||
      !this.state.poi ||
      !this.state.channelId;
    stopBtn.disabled = !isRunning && !isTransitioning;

    // Disable selects when bot is running
    zoneSelect.disabled = isRunning;
    poiSelect.disabled = isRunning;
    channelSelect.disabled = isRunning;
  },

  /**
   * Set UI loading state
   */
  setUILoading(loading) {
    const startBtn = document.getElementById("discord_start_btn");
    const stopBtn = document.getElementById("discord_stop_btn");

    startBtn.disabled = loading;
    stopBtn.disabled = loading;

    // Add/remove loading indicator (optional: add spinner CSS class)
    if (loading) {
      startBtn.classList.add("loading");
      stopBtn.classList.add("loading");
    } else {
      startBtn.classList.remove("loading");
      stopBtn.classList.remove("loading");
    }
  },

  /**
   * Show a message to the user
   */
  showMessage(message, type = "error") {
    const errorEl = document.getElementById("discord_error_message");
    if (!errorEl) return;

    if (type === "error") {
      errorEl.textContent = message;
      errorEl.className = "error-message";
      errorEl.style.display = "block";

      setTimeout(() => {
        errorEl.style.display = "none";
      }, 5000);
    } else if (type === "success") {
      // Show success message briefly (optional: different element)
      console.log("Success:", message);
    }
  },

  /**
   * Clean up on tool unload
   */
  destroy() {
    if (this.statusPollInterval) {
      clearInterval(this.statusPollInterval);
      this.statusPollInterval = null;
    }
  },
};

// Auto-initialize when tool is shown
document.addEventListener("toolshow", (e) => {
  if (e.detail?.toolId === "discord_bot") {
    DiscordBot.init();
  }
});

// Initialize on page load if tool might be visible
document.addEventListener("DOMContentLoaded", () => {
  // Only init if the tool container exists
  if (document.getElementById("tool_discord_bot")) {
    DiscordBot.init();
  }
});

// Clean up on page unload
window.addEventListener("beforeunload", () => {
  DiscordBot.destroy();
});
