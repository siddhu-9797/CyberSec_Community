// static/simulation_demo.js - FINAL INTERACTIVE VERSION (Using Logger)

document.addEventListener("DOMContentLoaded", () => {
  // Use Logger.info for top-level script load confirmation
  Logger.info("Interactive Simulation Demo Script Loaded (Using Logger).");

  // --- 1. DOM Element References --- (No changes needed here)
  const setupScreen = document.getElementById("setup-screen");
  const simulationInterface = document.getElementById("simulation-interface");
  const simHeaderTitle = document.getElementById("sim-scenario-title");
  const simPlayerInfo = document.getElementById("sim-player-info");
  const simTimeClock = document.getElementById("sim-time-clock");
  const simEndTime = document.getElementById("sim-end-time");
  const simIntensity = document.getElementById("sim-intensity");
  const simStatusIndicator = document.getElementById("sim-status-indicator");
  const simStatusText = document.getElementById("sim-status-text");
  const messageDisplay = document.getElementById("message-display");
  const playerInputForm = document.getElementById("player-input-form");
  const playerInput = document.getElementById("player-input");
  const systemStatusPanel = document.getElementById("system-status-panel");
  const systemStatusList = document.getElementById("system-status-list");
  const agentStatusPanel = document.getElementById("agent-status-panel");
  const agentStatusList = document.getElementById("agent-status-list");
  const missedCallsSection = document.getElementById("missed-calls-section");
  const missedCallsList = document.getElementById("missed-calls-list");
  const logFeedPanel = document.getElementById("log-feed-panel");
  const logFeedList = document.querySelector("#log-feed-panel .log-feed-list");
  const decisionPointContainer = document.getElementById(
    "decision-point-container"
  );
  const decisionTitle = document.getElementById("decision-title");
  const decisionSummary = document.getElementById("decision-summary");
  const decisionOptions = document.getElementById("decision-options");
  const analystBriefingContainer = document.getElementById(
    "analyst-briefing-container"
  );
  const analystBriefingContext = document.getElementById(
    "analyst-briefing-context"
  );
  const analystBriefingInput = document.getElementById(
    "analyst-briefing-input"
  );
  const submitBriefingButton = document.getElementById(
    "submit-briefing-button"
  );
  const yesNoPromptContainer = document.getElementById(
    "yes-no-prompt-container"
  );
  const yesNoPromptText = document.getElementById("yes-no-prompt-text");
  const debriefModal = document.getElementById("debrief-modal");
  const closeDebriefButton = document.getElementById("close-debrief-button");
  const debriefTitle = document.getElementById("debrief-title");
  const debriefSummaryPoints = document.getElementById(
    "debrief-summary-points"
  );
  const debriefFinalStatus = document.getElementById("debrief-final-status");
  const debriefPerformanceRating = document.getElementById(
    "debrief-performance-rating"
  );
  const ratingScores = document.getElementById("rating-scores");
  const ratingFeedback = document.getElementById("rating-feedback");
  const ratingError = document.getElementById("rating-error");
  const commandHelperBtn = document.getElementById("command-helper-btn");
  const commandDropdown = document.getElementById("command-dropdown");
  const allFocusButtons = document.querySelectorAll(".btn-panel-focus");
  const sideColumn = document.querySelector(".sim-column-side");
  const defocusPanelBtn = document.getElementById("defocus-panel-btn");
  const focusModeControls = document.getElementById("focus-mode-controls");
  const mainColumn = document.querySelector(".sim-column-main");
  const panelToggleButtons = document.querySelectorAll(".btn-panel-toggle");
  const startTourBtn = document.getElementById("start-tour-btn");
  const promptOverlay = document.getElementById("initial-prompt-overlay");
  const startTutorialButton = document.getElementById(
    "start-demo-tutorial-button"
  );
  const closeDemoButton = document.getElementById("close-demo-button");

  // --- Templates --- (No changes needed here)
  const systemStatusItemTemplate = document.getElementById(
    "system-status-item-template"
  );
  const agentStatusItemTemplate = document.getElementById(
    "agent-status-item-template"
  );
  const logFeedItemTemplate = document.getElementById("log-feed-item-template");
  const messageTemplate = document.getElementById("message-template");

  // --- 2. State Variables --- (No changes needed here)
  let localSimTime = null;
  let simTimerIntervalId = null;
  const SIM_TIMER_INTERVAL_MS = 1000;
  let demoState = "SETUP";
  let activeAgentCallButtons = {};
  let agentCurrentlyInConversation = null;
  let currentSystemStatus = {};
  let currentAgentStatus = {};
  let currentMissedCalls = [];
  let demoPlayerName = "You (CISO)";
  let currentlyFocusedPanel = null;
  let originalPanelParent = sideColumn;
  let lastSubmittedCommandForTour = "";

  // --- Shepherd Tour Variable ---
  let tour;

  // --- 3. Helper Functions --- (Refactored console calls)

  function formatTimeLocal(isoStringOrDate) {
    let dateObj;
    if (isoStringOrDate instanceof Date) dateObj = isoStringOrDate;
    else if (isoStringOrDate) {
      try {
        dateObj = new Date(isoStringOrDate);
      } catch (e) {}
    }
    if (!dateObj || isNaN(dateObj.getTime())) {
      Logger.warn("Invalid date/string for formatting:", isoStringOrDate);
      return "??:??:??";
    }
    try {
      const options = {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      };
      return dateObj.toLocaleTimeString(navigator.language, options);
    } catch (e) {
      Logger.error("Error formatting date:", {
        date: isoStringOrDate,
        error: e,
      });
      return "??:??:??";
    }
  }

  function stopSimTimer() {
    if (simTimerIntervalId) {
      Logger.debug("Stopping sim timer");
      clearInterval(simTimerIntervalId);
      simTimerIntervalId = null;
    }
  }

  function startSimTimer() {
    stopSimTimer();
    if (!localSimTime || isNaN(localSimTime.getTime())) {
      Logger.error("Cannot start sim timer: invalid localSimTime", {
        time: localSimTime,
      });
      return;
    }
    Logger.debug("Starting sim timer");
    simTimerIntervalId = setInterval(() => {
      if (!localSimTime || isNaN(localSimTime.getTime())) {
        Logger.warn("Stopping sim timer due to invalid time during interval.");
        stopSimTimer();
        return;
      }
      localSimTime.setSeconds(localSimTime.getSeconds() + 1);
      if (simTimeClock)
        simTimeClock.textContent = formatTimeLocal(localSimTime);
    }, SIM_TIMER_INTERVAL_MS);
  }

  // Placeholder API call function (Refactored console calls)
  async function apiCall(
    endpoint,
    method = "GET",
    body = null,
    includeAuth = false
  ) {
    Logger.warn(
      `[API Stub] Calling ${method} ${endpoint}`,
      body ? { body: body } : {}
    );
    await new Promise((resolve) => setTimeout(resolve, 300));
    if (method === "POST" && endpoint === "/sim/start_guest") {
      Logger.info("[API Stub] Simulating successful guest simulation start.");
      return { success: true, simulation_id: `guest_demo_${Date.now()}` };
    }
    if (method === "GET" && endpoint.startsWith("/sim/state/")) {
      Logger.info("[API Stub] Simulating successful state retrieval.");
      return { success: true, state: { status: "ENDED" } };
    }
    Logger.warn(
      `[API Stub] Unhandled stub for ${method} ${endpoint}. Returning failure.`
    );
    return { success: false, detail: "Unhandled API stub response" };
  }

  // --- 4. UI Update Functions --- (Refactored console calls)

  function addMessage(
    type,
    speaker,
    text,
    notification = null,
    isThinking = false,
    actionButtons = null
  ) {
    Logger.debug(
      `addMessage called: Type=${type}, Speaker=${speaker}, Text=${text.substring(
        0,
        30
      )}...`
    );
    if (!messageTemplate || !messageDisplay) {
      Logger.error(
        "addMessage: messageTemplate or messageDisplay element not found."
      );
      return;
    }
    try {
      const messageClone = messageTemplate.content.cloneNode(true);
      const messageDiv = messageClone.querySelector(".message");
      const speakerSpan = messageDiv.querySelector(".message-speaker");
      const textP = messageDiv.querySelector(".message-text");
      const notificationDiv = messageDiv.querySelector(".message-notification");
      const messageActionsDiv = messageDiv.querySelector(".message-actions");
      if (
        !messageDiv ||
        !speakerSpan ||
        !textP ||
        !notificationDiv ||
        !messageActionsDiv
      ) {
        Logger.error("addMessage: Template elements not found within clone.");
        return;
      }
      messageDiv.classList.add(type);
      if (speaker) speakerSpan.textContent = `${speaker}:`;
      else speakerSpan.remove();
      textP.textContent = text;
      if (notification) notificationDiv.textContent = `** ${notification} **`;
      else notificationDiv.remove();
      if (isThinking) textP.classList.add("thinking-animation");
      if (
        actionButtons &&
        Array.isArray(actionButtons) &&
        actionButtons.length > 0
      ) {
        messageActionsDiv.innerHTML = "";
        actionButtons.forEach((buttonConfig) => {
          if (!buttonConfig || !buttonConfig.text || !buttonConfig.command)
            return;
          const button = document.createElement("button");
          button.textContent = buttonConfig.text;
          button.classList.add("btn", ...(buttonConfig.classes || []));
          button.onclick = (event) => {
            event.stopPropagation();
            if (playerInput && playerInputForm) {
              playerInput.value = buttonConfig.command;
              playerInputForm.dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
              );
            }
            messageActionsDiv.classList.add("hidden");
            messageActionsDiv.innerHTML = "";
          };
          messageActionsDiv.appendChild(button);
        });
        messageActionsDiv.classList.remove("hidden");
      } else messageActionsDiv.remove();
      messageDiv.classList.add("message-appear");
      messageDisplay.insertBefore(messageDiv, messageDisplay.firstChild);
      messageDisplay.scrollTop = 0;
    } catch (error) {
      Logger.error("Error in addMessage:", { error: error });
    }
  }

  function updateSystemStatusUI(statusData) {
    Logger.debug("updateSystemStatusUI called:", statusData);
    if (!systemStatusList || !systemStatusItemTemplate) {
      Logger.error(
        "updateSystemStatusUI: systemStatusList or template not found."
      );
      return;
    }
    systemStatusList.innerHTML = "";
    currentSystemStatus = statusData || {};
    const sortedKeys = Object.keys(currentSystemStatus).sort();
    const addedItems = [];
    sortedKeys.forEach((key) => {
      try {
        const statusValue = currentSystemStatus[key] || "UNKNOWN";
        const itemClone = systemStatusItemTemplate.content.cloneNode(true);
        const li = itemClone.querySelector("li");
        const keySpan = li.querySelector(".status-key");
        const valueSpan = li.querySelector(".status-value");
        if (!li || !keySpan || !valueSpan) return;
        const baseStatus = statusValue.split(" ")[0].toUpperCase();
        li.dataset.systemKey = key;
        li.dataset.status = baseStatus;
        const readableKey = key.replace(/_/g, " ");
        const cleanedValue = statusValue.replace(/\(.*\)/g, "").trim();
        keySpan.textContent = readableKey;
        valueSpan.textContent = cleanedValue;
        systemStatusList.appendChild(li);
        addedItems.push(li);
      } catch (error) {
        Logger.error(`Error processing system status item ${key}:`, {
          error: error,
        });
      }
    });
    addedItems.forEach((item) => {
      item.classList.add("status-item-updated");
      setTimeout(() => {
        item.classList.remove("status-item-updated");
      }, 1500);
    });
  }

  function updateAgentStatusUI(agentStatusData) {
    Logger.debug("updateAgentStatusUI called:", agentStatusData);
    if (!agentStatusList || !agentStatusItemTemplate) {
      Logger.error(
        "updateAgentStatusUI: agentStatusList or template not found."
      );
      return;
    }
    agentStatusList.innerHTML = "";
    activeAgentCallButtons = {};
    currentAgentStatus = agentStatusData || {};
    const sortedNames = Object.keys(currentAgentStatus).sort();
    const addedItems = [];
    sortedNames.forEach((name) => {
      try {
        const state = currentAgentStatus[name] || "unknown";
        const itemClone = agentStatusItemTemplate.content.cloneNode(true);
        const li = itemClone.querySelector("li");
        const nameSpan = li.querySelector(".agent-name");
        const valueSpan = li.querySelector(".status-value");
        const callButton = li.querySelector(".btn-agent-call");
        const endCallButton = li.querySelector(".btn-agent-end-call");
        const thinkingIndicator = li.querySelector(".agent-thinking-indicator");
        if (
          !li ||
          !nameSpan ||
          !valueSpan ||
          !callButton ||
          !endCallButton ||
          !thinkingIndicator
        ) {
          Logger.error(
            `updateAgentStatusUI ERROR: Template elements missing for agent: ${name}`
          );
          return;
        }
        li.dataset.agentName = name; // Use the actual name (e.g., JAMES_BENNETT)
        li.dataset.state = state;
        const readableState = state.replace(/_/g, " ");
        nameSpan.textContent = name; // Display the actual name
        valueSpan.textContent = readableState;
        const newCallButton = callButton.cloneNode(true);
        const newEndCallButton = endCallButton.cloneNode(true);
        callButton.replaceWith(newCallButton);
        endCallButton.replaceWith(newEndCallButton);
        newCallButton.addEventListener("click", () =>
          handleAgentCallButton(name)
        );
        newEndCallButton.addEventListener("click", () =>
          handleEndCallButton(name)
        );
        activeAgentCallButtons[name] = {
          button: newCallButton,
          endButton: newEndCallButton,
          indicator: thinkingIndicator,
          listItem: li,
        };
        if (name === agentCurrentlyInConversation) {
          newCallButton.classList.add("hidden");
          newEndCallButton.classList.remove("hidden");
        } else {
          newCallButton.classList.remove("hidden");
          newEndCallButton.classList.add("hidden");
        }
        thinkingIndicator.classList.add("hidden");
        agentStatusList.appendChild(li);
        addedItems.push(li);
      } catch (error) {
        Logger.error(`Error processing agent status item ${name}:`, {
          error: error,
        });
      }
    });
    addedItems.forEach((item) => {
      item.classList.add("status-item-updated");
      setTimeout(() => {
        item.classList.remove("status-item-updated");
      }, 1500);
    });
  }

  function updateMissedCallsUI(missedCalls) {
    Logger.debug("updateMissedCallsUI called:", missedCalls);
    if (!missedCallsSection || !missedCallsList) {
      Logger.error("updateMissedCallsUI error: Required elements not found.");
      return;
    }
    currentMissedCalls = missedCalls || [];
    if (currentMissedCalls.length > 0) {
      missedCallsList.innerHTML = "";
      currentMissedCalls.forEach((name) => {
        const li = document.createElement("li");
        li.textContent = name; // Use the actual name (e.g., LAURA)
        const returnCallBtn = document.createElement("button");
        returnCallBtn.textContent = "Call Back";
        returnCallBtn.classList.add("btn", "btn-sm", "btn-return-call");
        returnCallBtn.onclick = () => handleAgentCallBackButton(name);
        li.appendChild(returnCallBtn);
        missedCallsList.appendChild(li);
      });
      missedCallsSection.classList.remove("hidden");
    } else {
      missedCallsList.innerHTML = "";
      missedCallsSection.classList.add("hidden");
    }
    Logger.debug("updateMissedCallsUI finished.");
  }

  function addLogFeedEntry(logData) {
    Logger.debug("addLogFeedEntry called:", logData);
    if (!logFeedList || !logFeedItemTemplate) {
      Logger.error("addLogFeedEntry: logFeedList or template not found.");
      return;
    }
    try {
      const itemClone = logFeedItemTemplate.content.cloneNode(true);
      const li = itemClone.querySelector("li");
      const timeSpan = li.querySelector(".log-time");
      const severitySpan = li.querySelector(".log-severity");
      const sourceSpan = li.querySelector(".log-source");
      const messageSpan = li.querySelector(".log-message");
      if (!li || !timeSpan || !severitySpan || !sourceSpan || !messageSpan)
        return;
      const timestamp = logData.timestamp
        ? formatTimeLocal(logData.timestamp)
        : formatTimeLocal(new Date());
      const severity = logData.severity || "INFO";
      const upperSeverity = severity.toUpperCase();
      const source = logData.source || "Demo";
      const message = logData.message || "No message";
      li.classList.add(`severity-${upperSeverity}`);
      timeSpan.textContent = timestamp;
      severitySpan.textContent = severity;
      severitySpan.className = `log-severity ${upperSeverity}`;
      sourceSpan.textContent = source;
      messageSpan.textContent = message;
      li.classList.add("log-appear");
      logFeedList.insertBefore(li, logFeedList.firstChild);
      const maxLogEntries = 50;
      while (logFeedList.children.length > maxLogEntries)
        logFeedList.removeChild(logFeedList.lastChild);
    } catch (error) {
      Logger.error("Error in addLogFeedEntry:", { error: error });
    }
  }

  function showDecisionPoint(payload) {
    Logger.debug("showDecisionPoint called");
    hideInteractionContainers();
    if (
      !decisionPointContainer ||
      !decisionTitle ||
      !decisionSummary ||
      !decisionOptions ||
      !playerInput
    ) {
      Logger.error("showDecisionPoint: Missing required elements.");
      return;
    }
    decisionTitle.textContent = payload.title || "Decision Required";
    decisionSummary.textContent = payload.summary || "No summary provided.";
    decisionOptions.innerHTML = "";
    if (payload.options && Array.isArray(payload.options)) {
      payload.options.forEach((opt) => {
        const button = document.createElement("button");
        button.textContent = opt.label;
        button.classList.add("btn", "btn-option");
        button.onclick = () => handleDecisionOptionClick(opt.value, opt.label);
        decisionOptions.appendChild(button);
      });
    }
    decisionPointContainer.classList.remove("hidden");
    playerInput.placeholder = "Click option above or type command...";
    playerInput.focus();
    demoState = "SHOWING_DECISION";
    Logger.info("demoState set to SHOWING_DECISION");
  }

  function showYesNoPrompt(payload) {
    Logger.debug("showYesNoPrompt called");
    hideInteractionContainers();
    if (!yesNoPromptContainer || !yesNoPromptText || !playerInput) {
      Logger.error("showYesNoPrompt: Missing required elements.");
      return;
    }
    const promptText = payload.prompt || "Enter 'yes' or 'no':";
    yesNoPromptText.textContent = promptText;
    yesNoPromptContainer.classList.remove("hidden");
    playerInput.placeholder = "Enter 'yes' or 'no'...";
    playerInput.focus();
    demoState = "SHOWING_YESNO";
    Logger.info("demoState set to SHOWING_YESNO");
  }

  function showAnalystBriefingInput(payload) {
    Logger.debug("showAnalystBriefingInput called");
    hideInteractionContainers();
    if (
      !analystBriefingContainer ||
      !analystBriefingContext ||
      !analystBriefingInput
    ) {
      Logger.error("showAnalystBriefingInput: Missing required elements.");
      return;
    }
    const contextQuestion =
      payload.context_question || "Prepare briefing points:";
    analystBriefingContext.textContent = contextQuestion;
    analystBriefingInput.value = "";
    analystBriefingContainer.classList.remove("hidden");
    analystBriefingInput.focus();
    demoState = "SHOWING_BRIEFING";
    Logger.info("demoState set to SHOWING_BRIEFING");
  }

  function hideInteractionContainers() {
    Logger.debug("Hiding interaction containers");
    if (decisionPointContainer) decisionPointContainer.classList.add("hidden");
    if (analystBriefingContainer)
      analystBriefingContainer.classList.add("hidden");
    if (yesNoPromptContainer) yesNoPromptContainer.classList.add("hidden");
    if (playerInput) playerInput.placeholder = "Enter command...";
    const wasInteracting = [
      "SHOWING_DECISION",
      "SHOWING_YESNO",
      "SHOWING_BRIEFING",
    ].includes(demoState);
    if (wasInteracting) {
      demoState = agentCurrentlyInConversation ? "IN_CONVERSATION" : "IDLE";
      Logger.info(
        `Interaction container hidden. Reset demoState to ${demoState}`
      );
    }
  }

  function setSimStatus(statusText, cssClass = null) {
    Logger.debug(`setSimStatus called: Text=${statusText}, Class=${cssClass}`);
    if (simStatusText) simStatusText.textContent = statusText;
    let finalCssClass = cssClass;
    if (!finalCssClass) {
      const lowerStatus = statusText.toLowerCase();
      if (lowerStatus.includes("running")) finalCssClass = "running";
      else if (lowerStatus.includes("paused")) finalCssClass = "paused";
      else if (lowerStatus.includes("ended")) finalCssClass = "ended";
      else if (lowerStatus.includes("error")) finalCssClass = "error";
      else finalCssClass = "";
    }
    if (simStatusIndicator)
      simStatusIndicator.className = `sim-status ${finalCssClass}`;
  }

  function showAgentThinking(agentName, isThinking) {
    Logger.debug(
      `showAgentThinking called: Agent=${agentName}, Thinking=${isThinking}`
    );
    const agentUI = activeAgentCallButtons[agentName];
    if (agentUI && agentUI.indicator)
      agentUI.indicator.classList.toggle("hidden", !isThinking);
    else
      Logger.warn(
        `Could not find UI elements for agent ${agentName} to show thinking.`
      );
  }

  function showDebriefModal(payload) {
    Logger.debug("showDebriefModal called");
    if (
      !debriefModal ||
      !debriefTitle ||
      !debriefSummaryPoints ||
      !debriefFinalStatus
    ) {
      Logger.error("Cannot show debrief, required modal elements missing.");
      return;
    }
    hideInteractionContainers();
    setSimStatus("Demo Ended", "ended");
    stopSimTimer();
    debriefTitle.textContent = payload.title || "-- Demo Debrief --";
    const summaryList = document.createElement("ul");
    (payload.summary_points || ["Demo completed."]).forEach((point) => {
      const li = document.createElement("li");
      li.textContent = point;
      summaryList.appendChild(li);
    });
    debriefSummaryPoints.innerHTML = "<h4>Summary</h4>";
    debriefSummaryPoints.appendChild(summaryList);
    const statusPre = document.createElement("pre");
    statusPre.textContent =
      payload.final_status_report ||
      JSON.stringify(currentSystemStatus, null, 2);
    debriefFinalStatus.innerHTML = "<h4>Final System Status</h4>";
    debriefFinalStatus.appendChild(statusPre);
    if (
      debriefPerformanceRating &&
      ratingScores &&
      ratingFeedback &&
      payload.rating
    ) {
      ratingScores.innerHTML = "";
      ratingFeedback.textContent = "";
      if (ratingError) ratingError.textContent = "";
      const createScoreItem = (label, score) => {
        /* ... (unchanged createScoreItem) ... */ const item =
          document.createElement("div");
        item.classList.add("rating-score-item");
        const labelSpan = document.createElement("span");
        labelSpan.classList.add("rating-label");
        labelSpan.textContent = label;
        const valueSpan = document.createElement("span");
        valueSpan.classList.add("rating-value");
        valueSpan.dataset.score = score;
        valueSpan.innerHTML = `${
          score ?? "?"
        } <span class="max-score">/ 10</span>`;
        item.appendChild(labelSpan);
        item.appendChild(valueSpan);
        return item;
      };
      ratingScores.appendChild(
        createScoreItem("Overall", payload.rating?.overall_score ?? null)
      );
      ratingScores.appendChild(
        createScoreItem("Timeliness", payload.rating?.timeliness_score ?? null)
      );
      ratingScores.appendChild(
        createScoreItem(
          "Contact Strategy",
          payload.rating?.contact_strategy_score ?? null
        )
      );
      ratingScores.appendChild(
        createScoreItem(
          "Decision Quality",
          payload.rating?.decision_quality_score ?? null
        )
      );
      ratingScores.appendChild(
        createScoreItem("Efficiency", payload.rating?.efficiency_score ?? null)
      );
      ratingFeedback.textContent =
        payload.rating?.qualitative_feedback || "Rating analysis complete.";
      debriefPerformanceRating.classList.remove("hidden");
    } else {
      Logger.warn(
        "Debrief rating elements or payload.rating missing. Skipping rating display."
      );
      if (debriefPerformanceRating)
        debriefPerformanceRating.classList.add("hidden");
    }
    debriefModal.classList.add("active");
    document.body.style.overflow = "hidden";
    demoState = "ENDED";
    Logger.info("demoState set to ENDED");
    if (playerInput) playerInput.disabled = true;
    if (playerInputForm) playerInputForm.classList.add("disabled");
  }

  function hideDebriefModal() {
    Logger.debug("hideDebriefModal called");
    if (debriefModal) {
      debriefModal.classList.remove("active");
      document.body.style.overflow = "";
    }
  }

  // --- 5. Demo Interaction Handlers --- (Refactored console calls)

  function handleAgentCallButton(agentName) {
    Logger.debug(
      `handleAgentCallButton: Trying to call ${agentName}. Current state: ${demoState}`
    );
    if (demoState === "IN_CONVERSATION") {
      addMessage(
        "system-warning",
        "Demo",
        `You are already in a call with ${agentCurrentlyInConversation}. Use 'hang up' first.`
      );
      return;
    }
    if (demoState === "ENDED") return;
    Logger.debug(`handleAgentCallButton: Proceeding to call ${agentName}`);
    addMessage("player", demoPlayerName, `call ${agentName}`);
    agentCurrentlyInConversation = agentName;
    demoState = "AWAITING_CALL_RESPONSE";
    Logger.info(
      `demoState set to AWAITING_CALL_RESPONSE. Agent: ${agentCurrentlyInConversation}`
    );
    if (playerInput)
      playerInput.placeholder = `Talking to ${agentName}... Type 'hang up' or click 🚫 to end.`;
    currentAgentStatus[agentName] = "on_call_with_cto";
    updateAgentStatusUI(currentAgentStatus);
    showAgentThinking(agentName, true);
    setTimeout(() => {
      Logger.debug(
        `handleAgentCallButton: Timeout fired for ${agentName}'s response. Current call: ${agentCurrentlyInConversation}`
      );
      if (agentCurrentlyInConversation !== agentName) {
        Logger.debug(
          `Call with ${agentName} ended before response timeout fired. Aborting response.`
        );
        showAgentThinking(agentName, false);
        return;
      }
      showAgentThinking(agentName, false);
      const response = getDemoAgentResponse(agentName, "initial");
      addMessage("agent", agentName, response);
      demoState = "IN_CONVERSATION";
      Logger.info(`demoState set to IN_CONVERSATION.`);
      // Check specifically for JAMES_BENNETT (formerly Hao Wang)
      if (agentName === "JAMES_BENNETT") {
        Logger.debug(
          "JAMES_BENNETT called. Triggering initial system updates."
        );
        triggerDemoSystemUpdate({ Auth_System: "HIGH_FAILURES" }, 500);
        triggerDemoLogEntry(
          {
            severity: "WARN",
            source: "Auth_System",
            message: "Unusual login patterns detected.",
          },
          700
        );
      }
    }, 2000 + Math.random() * 1500);
    Logger.debug(`handleAgentCallButton: Finished setup for ${agentName}.`);
  }

  function handleEndCallButton(agentName) {
    Logger.debug(
      `handleEndCallButton: Trying to end call with ${agentName}. Current state: ${demoState}, Current call: ${agentCurrentlyInConversation}`
    );
    if (demoState === "ENDED") return;
    if (
      agentCurrentlyInConversation !== agentName &&
      demoState !== "AWAITING_CALL_RESPONSE"
    ) {
      addMessage(
        "system-warning",
        "Demo",
        `Not in an active call with ${agentName}.`
      );
      if (activeAgentCallButtons[agentName]) {
        activeAgentCallButtons[agentName].button?.classList.remove("hidden");
        activeAgentCallButtons[agentName].endButton?.classList.add("hidden");
      }
      return;
    }
    Logger.debug(
      `handleEndCallButton: Proceeding to end call with ${agentName} via button.`
    );
    performHangUp(agentName); // No player message needed for button click
  }

  function handleAgentCallBackButton(agentName) {
    Logger.debug(
      `handleAgentCallBackButton: Trying call back ${agentName}. Current state: ${demoState}`
    );
    if (demoState === "IN_CONVERSATION") {
      addMessage(
        "system-warning",
        "Demo",
        `Finish your call with ${agentCurrentlyInConversation} first.`
      );
      return;
    }
    if (demoState === "ENDED") return;
    Logger.debug(
      `handleAgentCallBackButton: Proceeding call back ${agentName}`
    );
    addMessage("player", demoPlayerName, `call ${agentName}`);
    currentMissedCalls = currentMissedCalls.filter(
      (name) => name !== agentName
    );
    updateMissedCallsUI(currentMissedCalls);
    agentCurrentlyInConversation = agentName;
    demoState = "AWAITING_CALL_RESPONSE";
    Logger.info(
      `demoState set to AWAITING_CALL_RESPONSE. Agent: ${agentCurrentlyInConversation}`
    );
    if (playerInput)
      playerInput.placeholder = `Talking to ${agentName}... Type 'hang up' or click 🚫 to end.`;
    currentAgentStatus[agentName] = "on_call_with_cto";
    updateAgentStatusUI(currentAgentStatus);
    showAgentThinking(agentName, true);
    setTimeout(() => {
      Logger.debug(
        `handleAgentCallBackButton: Timeout fired for ${agentName}'s response. Current call: ${agentCurrentlyInConversation}`
      );
      if (agentCurrentlyInConversation !== agentName) {
        Logger.debug(
          `Callback with ${agentName} ended before timeout. Aborting response.`
        );
        showAgentThinking(agentName, false);
        return;
      }
      showAgentThinking(agentName, false);
      const response = getDemoAgentResponse(agentName, "callback");
      addMessage("agent", agentName, response);
      demoState = "IN_CONVERSATION";
      Logger.info(`demoState set to IN_CONVERSATION.`);
    }, 1500 + Math.random() * 1000);
    Logger.debug(`handleAgentCallBackButton: Finished setup for ${agentName}.`);
  }

  function handleDecisionOptionClick(value, label) {
    Logger.debug(
      `handleDecisionOptionClick: Clicked ${label}. Current state: ${demoState}`
    );
    if (demoState !== "SHOWING_DECISION") return;
    addMessage("player", demoPlayerName, `Selected Decision: ${label}`);
    hideInteractionContainers();
    processDemoDecision(value);
  }

  function processDemoPlayerInput(command) {
    Logger.debug(
      `processDemoPlayerInput: Received command "${command}". Current state: ${demoState}`
    );
    if (demoState === "ENDED") {
      Logger.debug("State is ENDED, ignoring command.");
      return;
    }
    const lowerCommand = command.toLowerCase().trim();
    let addPlayerMsg = ![
      "SHOWING_YESNO",
      "SHOWING_BRIEFING",
      "SHOWING_DECISION",
    ].includes(demoState);
    if (
      demoState === "SHOWING_YESNO" &&
      !(lowerCommand === "yes" || lowerCommand === "no")
    )
      addPlayerMsg = true;
    if (
      demoState === "SHOWING_DECISION" &&
      !["hold", "targeted", "broad", "decide"].some((kw) =>
        lowerCommand.includes(kw)
      )
    )
      addPlayerMsg = true;
    if (addPlayerMsg) addMessage("player", demoPlayerName, command);

    if (demoState === "SHOWING_YESNO") {
      hideInteractionContainers();
      if (lowerCommand === "yes")
        addMessage("system-info", "Demo", "You answered 'yes'.");
      else if (lowerCommand === "no")
        addMessage("system-info", "Demo", "You answered 'no'.");
      else {
        addMessage(
          "system-warning",
          "Demo",
          "Invalid input. Please answer 'yes' or 'no'."
        );
        showYesNoPrompt({
          prompt: yesNoPromptText?.textContent || "Enter 'yes' or 'no':",
        });
        return;
      }
      demoState = "IDLE";
      return;
    }
    if (demoState === "SHOWING_BRIEFING") {
      hideInteractionContainers();
      addMessage("system-info", "Demo", `Briefing submitted: "${command}"`);
      demoState = "IDLE";
      return;
    }
    if (demoState === "SHOWING_DECISION") {
      if (
        ["hold", "targeted", "broad"].some((kw) => lowerCommand.includes(kw))
      ) {
        hideInteractionContainers();
        processDemoDecision(lowerCommand);
      } else {
        addMessage(
          "system-warning",
          "Demo",
          "Please click an option or type 'hold', 'targeted', or 'broad'."
        );
      }
      return;
    }

    if (lowerCommand === "hang up" || lowerCommand === "hangup") {
      if (agentCurrentlyInConversation)
        performHangUp(agentCurrentlyInConversation);
      else addMessage("system-warning", "Demo", "No active call to hang up.");
    } else if (lowerCommand.startsWith("call ")) {
      const agentNameToCall = command.substring(5).trim();
      const knownAgents = Object.keys(currentAgentStatus);
      // Case-insensitive comparison for agent name
      const matchedAgent = knownAgents.find(
        (known) => known.toLowerCase() === agentNameToCall.toLowerCase()
      );
      if (matchedAgent) handleAgentCallButton(matchedAgent);
      else
        addMessage(
          "system-warning",
          "Demo",
          `Agent "${agentNameToCall}" not found. Available: ${knownAgents.join(
            ", "
          )}`
        );
    } else if (lowerCommand === "decide") {
      if (demoState === "IN_CONVERSATION")
        addMessage(
          "system-warning",
          "Demo",
          "Finish your call before making a decision."
        );
      else if (
        !currentSystemStatus.Auth_System ||
        !currentSystemStatus.Auth_System.includes("COMPROMISED")
      )
        addMessage(
          "system-warning",
          "Demo",
          "Need confirmation of compromise before deciding (wait for status update or ask agent)."
        );
      else showDemoDecisionPoint();
    } else if (lowerCommand.startsWith("isolate ")) {
      const target = command.substring(8).trim();
      if (target) performDemoIsolate(target);
      else
        addMessage(
          "system-warning",
          "Demo",
          "Specify what to isolate (e.g., 'isolate Auth_System')."
        );
    } else if (lowerCommand.startsWith("block ip ")) {
      const ip = command.substring(9).trim();
      if (ip && /^\d{1,3}(\.\d{1,3}){3}$/.test(ip)) performDemoBlockIp(ip);
      else
        addMessage(
          "system-warning",
          "Demo",
          "Specify a valid IP address to block (e.g., 'block ip 192.168.1.100')."
        );
    } else if (
      demoState === "IN_CONVERSATION" &&
      agentCurrentlyInConversation
    ) {
      const agentName = agentCurrentlyInConversation;
      showAgentThinking(agentName, true);
      setTimeout(() => {
        Logger.debug(
          `Timeout fired for ${agentName}'s response to "${lowerCommand}". Current call: ${agentCurrentlyInConversation}`
        );
        if (agentCurrentlyInConversation !== agentName) {
          Logger.debug(
            `Call ended before response timeout. Aborting response.`
          );
          showAgentThinking(agentName, false);
          return;
        }
        showAgentThinking(agentName, false);
        const response = getDemoAgentResponse(agentName, lowerCommand);
        addMessage("agent", agentName, response);
        // Check specifically for JAMES_BENNETT and 'status' keyword
        if (lowerCommand.includes("status") && agentName === "JAMES_BENNETT") {
          Logger.debug(
            "'status' keyword detected for JAMES_BENNETT. Triggering escalation & auto-ignore."
          );
          triggerDemoSystemUpdate(
            { Auth_System: "COMPROMISED", VPN_Access: "DEGRADED" },
            1000
          );
          triggerDemoLogEntry(
            {
              severity: "CRITICAL",
              source: "Auth_System",
              message: "Compromise detected!",
            },
            1200
          );
          triggerDemoLogEntry(
            {
              severity: "WARN",
              source: "VPN_Access",
              message: "Gateway degraded under unusual load.",
            },
            1300
          );
          setTimeout(() => {
            Logger.debug(
              "Timeout fired for JAMES_BENNETT's follow-up / auto-ignore. Current call:",
              agentCurrentlyInConversation
            );
            if (agentCurrentlyInConversation === agentName) {
              addMessage(
                "agent",
                agentName,
                "Just got an update - Auth system looks compromised, VPN is degraded! Recommend isolation."
              );
              const callerName = "LAURA"; // Formerly Paul Kahn
              if (currentAgentStatus[callerName] !== "available")
                currentAgentStatus[callerName] = "available";
              if (!currentMissedCalls.includes(callerName)) {
                currentMissedCalls.push(callerName);
                updateMissedCallsUI(currentMissedCalls);
              }
              updateAgentStatusUI(currentAgentStatus);
              addMessage(
                "system-info",
                "System",
                `(Simulated missed call from ${callerName} while you were busy with JAMES_BENNETT.)`
              );
              Logger.debug("Auto-ignore simulation complete.");
            } else
              Logger.debug("Call ended before auto-ignore timeout could fire.");
          }, 2500);
          // Check specifically for JAMES_BENNETT and 'recommend' keyword
        } else if (
          lowerCommand.includes("recommend") &&
          agentName === "JAMES_BENNETT"
        )
          addMessage(
            "agent",
            agentName,
            getDemoAgentResponse(agentName, "recommend")
          );
      }, 1500 + Math.random() * 1000);
    } else {
      if (demoState === "IDLE")
        addMessage(
          "system-warning",
          "Demo",
          `Command "${command}" not recognized... Try 'call <name>', 'hang up', 'decide', 'isolate <system>', 'block ip <ip>'. Use ☰ for hints.`
        );
      else Logger.debug(`Command "${command}" ignored in state ${demoState}.`);
    }
    Logger.debug(`processDemoPlayerInput finished for command "${command}"`);
  }

  function performHangUp(agentName) {
    Logger.debug(`performHangUp started for ${agentName}`);
    const wasInConversation = agentCurrentlyInConversation === agentName;
    const previousAgent = agentCurrentlyInConversation;
    agentCurrentlyInConversation = null;
    demoState = "IDLE";
    Logger.info(`demoState set to IDLE.`);
    if (playerInput) playerInput.placeholder = "Enter command...";
    if (
      currentAgentStatus[agentName] &&
      currentAgentStatus[agentName] !== "available"
    )
      currentAgentStatus[agentName] = "available";
    if (
      previousAgent &&
      previousAgent !== agentName &&
      currentAgentStatus[previousAgent] !== "available"
    ) {
      currentAgentStatus[previousAgent] = "available";
      Logger.debug(
        `Made previous agent ${previousAgent} available due to hangup state mismatch.`
      );
    }
    updateAgentStatusUI(currentAgentStatus);
    if (wasInConversation)
      addMessage(
        "system-conversation",
        "Conversation",
        `Ended conversation with ${agentName}.`
      );
    else
      addMessage(
        "system-info",
        "System",
        `Call attempt with ${agentName} cancelled.`
      );
    const agentToStopThinking = previousAgent || agentName;
    if (
      agentToStopThinking &&
      activeAgentCallButtons[agentToStopThinking]?.indicator
    ) {
      activeAgentCallButtons[agentToStopThinking].indicator.classList.add(
        "hidden"
      );
      Logger.debug(`Hid thinking indicator for ${agentToStopThinking}`);
    }
    Logger.debug(`performHangUp finished for ${agentName}`);
  }

  function getDemoAgentResponse(agentName, inputKeyword) {
    Logger.debug(
      `getDemoAgentResponse called for ${agentName}, keyword: ${inputKeyword}`
    );
    const responses = {
      // Updated agent names as keys
      JAMES_BENNETT: {
        initial: "Hey Jill. What's up? Seeing some alerts here.",
        callback: "Hi Jill, you called? Just analyzing some network logs.",
        status:
          "Checking the system status... Auth looks shaky, seeing high failures. VPN seems slow too.",
        help: "I'm looking into the Auth system alerts now. What do you need?",
        isolate:
          "Isolating systems? Which one specifically? Recommend isolating Auth_System if you see compromise.",
        recommend:
          "Based on the Auth compromise, I recommend isolating it immediately. Type 'isolate Auth_System'.",
        default: "Okay, got it. Let me check on that.",
      },
      LAURA: {
        initial: "CTO? Hi. Things seem... unstable. Lots of errors.",
        callback:
          "Yeah, Jill? Sorry missed your call earlier. What's going on?",
        status:
          "Status? It's bad. Seeing database connection errors and file server access issues.",
        help: "Need help? I'm trying to stabilize the file servers.",
        default: "Understood. I'll keep you updated.",
      },
      ETHAN_KIM: {
        initial: "Hi CTO. Monitoring dashboards are lighting up red.",
        callback: "Yes, CTO? Was just about to escalate some security alerts.",
        status:
          "Auth system failures, high network traffic on segment Gamma7... doesn't look good.",
        help: "I'm correlating IDS alerts. Looks like potential ransomware activity.",
        default: "Acknowledged.",
      },
      CEO: {
        initial: "Jill? What's the situation? Is it serious?",
        callback: "Jill, finally! What's the latest? Are we under attack?",
        status: "Just tell me, are customer operations affected?",
        default: "Okay, keep me informed. Need to manage external comms.",
      },
      "Legal Counsel": {
        initial: "CTO. Reporting in. Any legal implications yet?",
        callback:
          "Yes, Jill? Following the situation. Let me know if we need to invoke the incident response plan legally.",
        status:
          "Have we confirmed a data breach? That changes our obligations.",
        default: "Noted. Standing by.",
      },
      "PR Head": {
        initial:
          "Jill - need to know what's happening. Media might catch wind.",
        callback: "Hi Jill. Any update? Do we need to prepare a statement?",
        status:
          "Are customer services down? What can I tell the public if asked?",
        default: "Okay, waiting for your direction on communications.",
      },
    };
    const agentResponses = responses[agentName] || { default: "Okay." };
    const lowerInput = inputKeyword.toLowerCase();
    let response = agentResponses.default;
    if (inputKeyword === "initial")
      response = agentResponses.initial || response;
    else if (inputKeyword === "callback")
      response = agentResponses.callback || response;
    else if (lowerInput.includes("status"))
      response = agentResponses.status || response;
    else if (lowerInput.includes("help") || lowerInput.includes("update"))
      response = agentResponses.help || response;
    else if (lowerInput.includes("isolate"))
      response = agentResponses.isolate || response;
    else if (lowerInput.includes("recommend") && agentResponses.recommend)
      response = agentResponses.recommend;
    Logger.debug(`getDemoAgentResponse returning: "${response}"`);
    return response;
  }

  function triggerDemoSystemUpdate(updatePayload, delay = 0) {
    Logger.debug(
      `Setting timeout ${delay}ms for triggerDemoSystemUpdate:`,
      updatePayload
    );
    setTimeout(() => {
      Logger.debug("Timeout fired for triggerDemoSystemUpdate:", updatePayload);
      const updatedStatus = { ...currentSystemStatus, ...updatePayload };
      updateSystemStatusUI(updatedStatus);
      for (const key in updatePayload) {
        addMessage(
          "system-info",
          "Status Change",
          `System ${key.replace(/_/g, " ")} -> ${updatePayload[key]}`
        );
      }
    }, delay);
  }

  function triggerDemoLogEntry(logPayload, delay = 0) {
    Logger.debug(
      `Setting timeout ${delay}ms for triggerDemoLogEntry:`,
      logPayload
    );
    setTimeout(() => {
      Logger.debug("Timeout fired for triggerDemoLogEntry:", logPayload);
      addLogFeedEntry({ timestamp: new Date().toISOString(), ...logPayload });
    }, delay);
  }

  function showDemoDecisionPoint() {
    Logger.debug("showDemoDecisionPoint called");
    const summary = `Demo Decision Point:\nSystem Status:\n${JSON.stringify(
      currentSystemStatus,
      null,
      2
    )}`;
    const options = [
      { value: "Hold", label: "Hold Action (Monitor)" },
      { value: "Targeted", label: "Targeted Isolation (Auth_System)" },
      { value: "Broad", label: "Broad Shutdown (Network)" },
    ];
    showDecisionPoint({
      title: "Demo: Containment Strategy",
      summary: summary,
      options: options,
    });
  }

  function processDemoDecision(decisionValue) {
    Logger.debug("processDemoDecision called with:", decisionValue);
    let chosenLabel = decisionValue;
    const decisionLower = decisionValue.toLowerCase();
    let ratingAdjustment = 0;
    if (decisionLower.includes("targeted")) {
      chosenLabel = "Targeted Isolation";
      Logger.info("Decision is Targeted");
      ratingAdjustment = 2;
    } else if (decisionLower.includes("broad")) {
      chosenLabel = "Broad Shutdown";
      Logger.info("Decision is Broad");
      ratingAdjustment = -1;
    } else if (decisionLower.includes("hold")) {
      chosenLabel = "Hold Action";
      Logger.info("Decision is Hold");
      ratingAdjustment = -1;
    } else {
      Logger.warn(
        `Unrecognized decision value: ${decisionValue}. Defaulting to 'Hold'.`
      );
      chosenLabel = "Hold Action (Default)";
      ratingAdjustment = -2;
    }
    addMessage(
      "system-decision",
      "Demo Decision",
      `Directive Chosen: ${chosenLabel}`
    );
    let summaryPoints = [`Decision Made: ${chosenLabel}`];
    let finalReport = { ...currentSystemStatus };
    if (chosenLabel.includes("Targeted")) {
      summaryPoints.push("Targeted isolation of Auth_System initiated.");
      finalReport["Auth_System"] = "ISOLATED (Manual)";
      triggerDemoSystemUpdate({ Auth_System: "ISOLATED (Manual)" }, 500);
      triggerDemoLogEntry(
        {
          severity: "INFO",
          source: "Manual Action",
          message: "Auth_System isolation requested.",
        },
        200
      );
    } else if (chosenLabel.includes("Broad")) {
      summaryPoints.push(
        "Broad network shutdown initiated, causing wider impact."
      );
      finalReport["Network_Segment_Internal"] = "OFFLINE (Manual)";
      finalReport["Network_Segment_Gamma7"] = "OFFLINE (Manual)";
      finalReport["Website_Public"] = "OFFLINE";
      finalReport["VPN_Access"] = "OFFLINE";
      triggerDemoSystemUpdate(
        {
          Network_Segment_Internal: "OFFLINE (Manual)",
          Network_Segment_Gamma7: "OFFLINE (Manual)",
          Website_Public: "OFFLINE",
          VPN_Access: "OFFLINE",
        },
        500
      );
      triggerDemoLogEntry(
        {
          severity: "WARN",
          source: "Manual Action",
          message: "Broad network shutdown requested.",
        },
        200
      );
    } else {
      summaryPoints.push(
        "Monitoring continues. Attacker likely continues activity."
      );
      triggerDemoLogEntry(
        {
          severity: "INFO",
          source: "Manual Action",
          message: `Decision: ${chosenLabel}.`,
        },
        200
      );
      triggerDemoSystemUpdate(
        { File_Servers: "ENCRYPTING", Customer_Database: "EXFILTRATING" },
        1500
      );
      finalReport["File_Servers"] = "ENCRYPTING";
      finalReport["Customer_Database"] = "EXFILTRATING";
    }
    Logger.debug("Setting timeout for showDebriefModal");
    setTimeout(() => {
      showDebriefModal({
        title: "Demo Scenario Debrief",
        summary_points: summaryPoints,
        final_status_report: `Final Demo State:\n${JSON.stringify(
          finalReport,
          null,
          2
        )}`,
        rating: {
          overall_score: Math.max(4, Math.min(10, 6 + ratingAdjustment)),
          timeliness_score: 7,
          contact_strategy_score: 6,
          decision_quality_score: Math.max(
            1,
            Math.min(10, 7 + ratingAdjustment * 2)
          ),
          efficiency_score: chosenLabel.includes("Broad") ? 3 : 5,
          qualitative_feedback: `You chose '${chosenLabel}'. ${
            chosenLabel.includes("Targeted")
              ? "Targeted isolation was a good first step here."
              : chosenLabel.includes("Broad")
              ? "Broad shutdown contained the issue but caused unnecessary downtime."
              : "Holding action allowed the situation to worsen."
          } In a real scenario, consequences would follow.`,
        },
      });
    }, 2000);
  }

  function performDemoIsolate(target) {
    Logger.debug(`performDemoIsolate called for: ${target}`);
    addMessage(
      "system-info",
      "Demo Action",
      `Initiating isolation for ${target}...`
    );
    let systemKey = null;
    const lowerTarget = target.toLowerCase().replace(/ /g, "_");
    systemKey = Object.keys(currentSystemStatus).find(
      (key) => key.toLowerCase() === lowerTarget
    );
    if (!systemKey)
      systemKey = Object.keys(currentSystemStatus).find((key) =>
        key.toLowerCase().includes(lowerTarget)
      );
    if (
      systemKey &&
      currentSystemStatus[systemKey] &&
      !currentSystemStatus[systemKey].includes("ISOLATED")
    ) {
      Logger.debug(`Found matching system key: ${systemKey}`);
      triggerDemoSystemUpdate({ [systemKey]: "ISOLATING..." }, 500);
      triggerDemoLogEntry(
        {
          severity: "INFO",
          source: "Manual Action",
          message: `Isolation requested for ${systemKey}.`,
        },
        200
      );
      setTimeout(
        () =>
          triggerDemoSystemUpdate({ [systemKey]: "ISOLATED (Manual)" }, 1000),
        1500
      );
    } else if (
      systemKey &&
      currentSystemStatus[systemKey] &&
      currentSystemStatus[systemKey].includes("ISOLATED")
    )
      addMessage(
        "system-info",
        "Demo",
        `System '${systemKey.replace(/_/g, " ")}' is already isolated.`
      );
    else {
      Logger.warn(`No matching system key found for ${target}`);
      addMessage(
        "system-warning",
        "Demo",
        `System target '${target}' not found or invalid. Available: ${Object.keys(
          currentSystemStatus
        )
          .map((k) => k.replace(/_/g, " "))
          .join(", ")}`
      );
    }
  }

  function performDemoBlockIp(ip) {
    Logger.debug(`performDemoBlockIp called for: ${ip}`);
    addMessage(
      "system-info",
      "Demo Action",
      `Blocking IP address ${ip} at firewall...`
    );
    triggerDemoLogEntry(
      {
        severity: "INFO",
        source: "Manual Action",
        message: `Firewall rule added to block IP ${ip}.`,
      },
      500
    );
  }

  // --- 6. Shepherd.js Tour Definition --- (Refactored console calls)

  const waitForElement = (selector, filterFn = null, timeout = 5000) => {
    /* ... (Keep corrected waitForElement) ... */
    return new Promise((resolve, reject) => {
      const intervalTime = 100;
      let elapsedTime = 0;
      const interval = setInterval(() => {
        const elements = document.querySelectorAll(selector);
        let foundElement = null;
        if (elements.length > 0) {
          if (filterFn && typeof filterFn === "function") {
            try {
              foundElement = Array.from(elements).find((el) => filterFn(el));
            } catch (filterError) {
              Logger.error(
                `[Tour] Error executing filterFn for selector "${selector}":`,
                filterError
              );
            }
          } else {
            foundElement = elements[0];
          }
        }
        if (foundElement) {
          clearInterval(interval);
          Logger.debug(
            `[Tour] waitForElement resolved for selector "${selector}"`,
            foundElement
          );
          resolve(foundElement);
        } else {
          elapsedTime += intervalTime;
          if (elapsedTime >= timeout) {
            clearInterval(interval);
            Logger.error(
              `[Tour] Timeout waiting for element: ${selector}` +
                (filterFn ? " with filter" : "")
            );
            reject(
              new Error(
                `Element ${selector} not found` +
                  (filterFn ? " matching filter" : "") +
                  ` within ${timeout}ms`
              )
            );
          }
        }
      }, intervalTime);
    });
  };

  const waitForEvent = (
    targetElementOrSelector,
    eventType,
    conditionFn = () => true,
    timeout = 10000
  ) => {
    /* ... (Keep corrected waitForEvent) ... */
    return new Promise(async (resolve, reject) => {
      let target;
      if (typeof targetElementOrSelector === "string") {
        try {
          target = await waitForElement(targetElementOrSelector, null, timeout);
        } catch (err) {
          reject(err);
          return;
        }
      } else target = targetElementOrSelector;
      if (!target) {
        reject(
          new Error("Target element not found or provided for waitForEvent")
        );
        return;
      }
      let listener;
      const timer = setTimeout(() => {
        target.removeEventListener(eventType, listener);
        Logger.warn(
          `[Tour] Timeout waiting for event '${eventType}' on`,
          target
        );
        reject(new Error(`Timeout waiting for ${eventType} event`));
      }, timeout);
      listener = (event) => {
        try {
          if (conditionFn(event)) {
            clearTimeout(timer);
            target.removeEventListener(eventType, listener);
            Logger.debug(
              `[Tour] Event '${eventType}' received and condition met.`,
              event
            );
            resolve(event);
          } else
            Logger.debug(
              `[Tour] Event '${eventType}' received but condition NOT met.`
            );
        } catch (conditionError) {
          Logger.error(
            `[Tour] Error executing conditionFn for event '${eventType}':`,
            conditionError
          );
        }
      };
      target.addEventListener(eventType, listener);
      Logger.debug(`[Tour] Added '${eventType}' listener to`, target);
      const cleanup = () => {
        clearTimeout(timer);
        target.removeEventListener(eventType, listener);
        Logger.debug(
          `[Tour] Event listener cleanup for '${eventType}' due to tour cancel/complete.`
        );
        if (tour) {
          tour.off("cancel", cleanup);
          tour.off("complete", cleanup);
        }
      };
      if (tour) {
        tour.once("cancel", cleanup);
        tour.once("complete", cleanup);
      } else
        Logger.warn(
          "[Tour] Tour object not available to attach cleanup listeners in waitForEvent."
        );
    });
  };

  function initializeTour() {
    if (tour && tour.isActive()) tour.cancel();
    Logger.info("[Tour] Initializing Shepherd Tour");
    tour = new Shepherd.Tour({
      useModalOverlay: false,
      defaultStepOptions: {
        classes: "shepherd-theme-arrows shepherd-custom",
        scrollTo: { behavior: "smooth", block: "center" },
        cancelIcon: { enabled: true },
      },
    });
    // --- Tour Steps --- (Refactored console calls inside step logic)
    tour.addStep({
      id: "intro",
      text: 'Welcome! This tour will guide you through the simulation interface and a basic incident response flow. Click "Next".',
      attachTo: { element: ".sim-header", on: "bottom" },
      buttons: [{ action: tour.next, text: "Next" }],
    });
    tour.addStep({
      id: "explain-header",
      text: "The header shows the scenario, your role, the simulation clock, and overall status.",
      attachTo: { element: ".sim-header", on: "bottom" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
    });
    tour.addStep({
      id: "explain-messages",
      text: "Messages from agents, system alerts, and your commands appear here (newest at top).",
      attachTo: { element: "#message-display", on: "right" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
    });
    tour.addStep({
      id: "explain-system-status",
      text: "This panel tracks the real-time status of critical systems.",
      attachTo: { element: "#system-status-panel", on: "left" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
    });
    tour.addStep({
      id: "explain-agent-status",
      text: "See your team's availability here. Use the icons to Call (📞) or Hang Up (🚫).",
      attachTo: { element: "#agent-status-panel", on: "left" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
    });
    tour.addStep({
      id: "explain-log-feed",
      text: "Detailed technical logs appear here, providing evidence for status changes.",
      attachTo: { element: "#log-feed-panel", on: "left" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
    });
    tour.addStep({
      id: "explain-input",
      text: "Type commands here (e.g., `call Name`, `status?`, `isolate System`, `decide`). Use ☰ for hints.",
      attachTo: { element: "#player-input-form", on: "top" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
    });
    // Interactive Part 1: Call JAMES_BENNETT
    tour.addStep({
      id: "start-interactive-call",
      text: "Let's start. Click the blue Call (📞) button next to 'JAMES_BENNETT'.", // Updated Name
      attachTo: {
        element: 'li[data-agent-name="JAMES_BENNETT"] .btn-agent-call', // Updated Selector
        on: "left",
      },
      buttons: [],
      beforeShowPromise: () =>
        waitForElement(
          'li[data-agent-name="JAMES_BENNETT"] .btn-agent-call', // Updated Selector
          null,
          5000
        ),
      when: {
        show() {
          Logger.debug("[Tour] Showing step 'start-interactive-call'");
          waitForEvent(
            'li[data-agent-name="JAMES_BENNETT"] .btn-agent-call', // Updated Selector
            "click"
          )
            .then(() => {
              Logger.debug(
                "[Tour] JAMES_BENNETT call button clicked. Advancing."
              ); // Updated Log
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "start-interactive-call"
              )
                tour.next();
            })
            .catch((err) =>
              Logger.error(
                "[Tour] Error/Timeout waiting for JAMES_BENNETT call click:", // Updated Log
                err
              )
            );
        },
      },
    });
    tour.addStep({
      id: "observe-call-start",
      text: "Excellent. Notice JAMES_BENNETT's status is now 'on call...' and you received his initial message.", // Updated Name
      attachTo: {
        element: '#agent-status-list li[data-agent-name="JAMES_BENNETT"]', // Updated Selector
        on: "left",
      },
      buttons: [{ action: tour.next, text: "Next" }],
      beforeShowPromise: () =>
        waitForElement(
          '#agent-status-list li[data-agent-name="JAMES_BENNETT"][data-state="on_call_with_cto"]', // Updated Selector
          null,
          5000
        ),
    });
    // Interactive Part 2: Ask Status
    tour.addStep({
      id: "type-status",
      text: "Ask JAMES_BENNETT for details. Type `status?` in the input below and press Enter or click the Send button.", // Updated Name
      attachTo: { element: "#player-input", on: "top" },
      buttons: [],
      when: {
        show() {
          Logger.debug("[Tour] Showing step 'type-status'");
          if (playerInput) playerInput.focus();
          waitForEvent(
            playerInputForm,
            "submit",
            (event) => {
              const checkCommand = lastSubmittedCommandForTour
                .toLowerCase()
                .trim();
              Logger.debug(
                "[Tour] Submit event for 'type-status', checking command:",
                checkCommand
              );
              return checkCommand.includes("status");
            },
            15000
          )
            .then(() => {
              Logger.debug("[Tour] 'status' command submitted. Advancing.");
              lastSubmittedCommandForTour = "";
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "type-status"
              )
                tour.next();
            })
            .catch((err) => {
              Logger.error(
                "[Tour] Error/Timeout waiting for status submit:",
                err
              );
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "type-status"
              )
                alert(
                  "Timeout: Please type a command including 'status' and press Enter."
                );
            });
        },
      },
    });
    tour.addStep({
      id: "observe-escalation",
      text: "Status requested! See 'Auth System' become 'COMPROMISED', VPN 'DEGRADED', new critical logs, and JAMES_BENNETT's urgent update. Click 'Next'.", // Updated Name
      attachTo: { element: "#system-status-panel", on: "left" },
      buttons: [{ action: tour.next, text: "Next" }],
      beforeShowPromise: async () => {
        try {
          Logger.debug(
            "[Tour] observe-escalation: Waiting for COMPROMISED status..."
          );
          await waitForElement(
            '#system-status-list li[data-system-key="Auth_System"][data-status="COMPROMISED"]',
            null,
            8000
          );
          Logger.debug(
            "[Tour] observe-escalation: COMPROMISED status found. Waiting for JAMES_BENNETT's follow-up message..." // Updated Log
          );
          await waitForElement(
            ".message.agent .message-speaker",
            (el) =>
              el.textContent.includes("JAMES_BENNETT") && // Updated Name Check
              el
                .closest(".message")
                ?.querySelector(".message-text")
                ?.textContent.includes("Just got an update"),
            8000
          );
          Logger.debug(
            "[Tour] observe-escalation: JAMES_BENNETT's follow-up message found." // Updated Log
          );
          await new Promise((resolve) => setTimeout(resolve, 300));
        } catch (error) {
          Logger.error(
            "[Tour] Error in beforeShowPromise for observe-escalation:",
            error
          );
          if (tour && tour.isActive()) tour.cancel();
          alert(
            "Error: Could not find expected status updates or messages for the tour."
          );
          throw error;
        }
      },
    });
    tour.addStep({
      id: "observe-missed-call-skipped",
      text: "While you were talking, LAURA tried to call (see 'Missed Calls'). In this demo, we assume you correctly focused on JAMES_BENNETT. Click 'Next'.", // Updated Names
      attachTo: { element: "#missed-calls-section", on: "left" },
      buttons: [
        {
          action: tour.back,
          classes: "shepherd-button-secondary",
          text: "Back",
        },
        { action: tour.next, text: "Next" },
      ],
      beforeShowPromise: () =>
        waitForElement("#missed-calls-list li", null, 5000),
    });
    // *** MODIFIED STEP: Click Hang Up Button ***
    tour.addStep({
      id: "click-hang-up",
      text: "The situation has escalated. Before making a decision, end the call with JAMES_BENNETT by clicking the red Hang Up (🚫) button next to his name.", // Updated Name
      attachTo: {
        element:
          'li[data-agent-name="JAMES_BENNETT"] .btn-agent-end-call:not(.hidden)', // Updated Selector
        on: "left",
      },
      buttons: [],
      beforeShowPromise: () =>
        waitForElement(
          'li[data-agent-name="JAMES_BENNETT"] .btn-agent-end-call:not(.hidden)', // Updated Selector
          null,
          5000
        ),
      when: {
        show() {
          Logger.debug("[Tour] Showing step 'click-hang-up'");
          waitForEvent(
            'li[data-agent-name="JAMES_BENNETT"] .btn-agent-end-call', // Updated Selector
            "click"
          )
            .then(() => {
              Logger.debug("[Tour] End call button clicked. Advancing.");
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "click-hang-up"
              )
                setTimeout(() => tour.next(), 100);
            })
            .catch((err) => {
              Logger.error(
                "[Tour] Error/Timeout waiting for end call click:",
                err
              );
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "click-hang-up"
              )
                alert(
                  "Timeout: Please click the red Hang Up button next to JAMES_BENNETT." // Updated Alert
                );
            });
        },
      },
    });
    // Interactive Part 3: Decide
    tour.addStep({
      id: "type-decide",
      text: "Okay, the call is ended. Now it's time to decide on containment. Type `decide` and press Enter or click Send.",
      attachTo: { element: "#player-input", on: "top" },
      buttons: [],
      beforeShowPromise: () =>
        new Promise((resolve, reject) => {
          let checkCount = 0;
          const maxChecks = 25;
          const checkIdle = () => {
            if (demoState === "IDLE" && !agentCurrentlyInConversation) {
              Logger.debug(
                "[Tour] Verified state is IDLE for type-decide step."
              );
              resolve();
            } else if (checkCount++ < maxChecks) {
              Logger.debug(
                "[Tour] Waiting for state to become IDLE for type-decide step..."
              );
              setTimeout(checkIdle, 200);
            } else {
              Logger.error(
                "[Tour] Timeout waiting for state to become IDLE before type-decide step."
              );
              reject(new Error("State did not become IDLE"));
            }
          };
          checkIdle();
        }).catch((err) => {
          if (tour && tour.isActive()) tour.cancel();
          alert("Error: State issue before decide step.");
          throw err;
        }),
      when: {
        show() {
          Logger.debug("[Tour] Showing step 'type-decide'");
          if (playerInput) playerInput.focus();
          waitForEvent(
            playerInputForm,
            "submit",
            (event) => {
              const checkCommand = lastSubmittedCommandForTour
                .toLowerCase()
                .trim();
              Logger.debug(
                "[Tour] Submit event for 'type-decide', checking command:",
                checkCommand
              );
              return checkCommand === "decide";
            },
            15000
          )
            .then(() => {
              Logger.debug("[Tour] 'decide' command submitted. Advancing.");
              lastSubmittedCommandForTour = "";
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "type-decide"
              )
                tour.next();
            })
            .catch((err) => {
              Logger.error(
                "[Tour] Error/Timeout waiting for decide submit:",
                err
              );
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "type-decide"
              )
                alert("Timeout: Please type exactly 'decide' and press Enter.");
            });
        },
      },
    });
    tour.addStep({
      id: "observe-decision-point",
      text: "The 'Decision Required' options appear, summarizing the current state. Click 'Next'.",
      attachTo: { element: "#decision-point-container", on: "bottom" },
      buttons: [{ action: tour.next, text: "Next" }],
      beforeShowPromise: () =>
        waitForElement("#decision-point-container:not(.hidden)", null, 5000),
    });
    // Interactive Part 4: Click Decision
    tour.addStep({
      id: "click-decision-option",
      text: "Choose targeted isolation, often a good first step. Click the 'Targeted Isolation (Auth_System)' button.",
      attachTo: {
        element: () =>
          Array.from(
            document.querySelectorAll("#decision-options .btn-option")
          ).find((btn) => btn.textContent.includes("Targeted Isolation")),
        on: "bottom",
      },
      buttons: [],
      beforeShowPromise: () =>
        waitForElement("#decision-options .btn-option", null, 5000),
      when: {
        show() {
          Logger.debug("[Tour] Showing step 'click-decision-option'");
          let docClickListener;
          const cleanup = () => {
            document.removeEventListener("click", docClickListener);
            Logger.debug(
              "[Tour] Removed doc click listener for decision step."
            );
            if (tour) {
              tour.off("cancel", cleanup);
              tour.off("complete", cleanup);
            }
          };
          docClickListener = (event) => {
            const targetButton = event.target.closest(
              "#decision-options .btn-option"
            );
            if (
              targetButton &&
              targetButton.textContent.includes("Targeted Isolation")
            ) {
              Logger.debug(
                "[Tour] Targeted Isolation button clicked. Advancing."
              );
              cleanup();
              if (
                tour &&
                tour.isActive() &&
                tour.currentStep?.id === "click-decision-option"
              )
                tour.next();
            } else if (targetButton) {
              Logger.debug(
                "[Tour] Clicked a decision button, but not the correct one."
              );
              alert(
                "Please click the 'Targeted Isolation' button for this tour step."
              );
            }
          };
          document.addEventListener("click", docClickListener);
          Logger.debug("[Tour] Added doc click listener for decision step.");
          if (tour) {
            tour.once("cancel", cleanup);
            tour.once("complete", cleanup);
          }
        },
      },
    });
    tour.addStep({
      id: "observe-debrief",
      text: "Decision made! The simulation ends, showing the Debrief modal with summary and rating. Click 'End Tour'.",
      attachTo: { element: "#debrief-modal .sim-modal-content", on: "top" },
      buttons: [{ action: tour.complete, text: "End Tour" }],
      beforeShowPromise: () =>
        waitForElement("#debrief-modal.active", null, 5000),
    });
    // Tour Event Handlers
    tour.on("complete", () => {
      Logger.info("[Tour] Tour completed!");
      try {
        if (typeof confetti === "function")
          confetti({ particleCount: 150, spread: 100, origin: { y: 0.6 } });
        else Logger.warn("[Tour] Confetti function not found.");
      } catch (e) {
        Logger.error("[Tour] Error triggering confetti:", e);
      }
      setTimeout(
        () =>
          addMessage(
            "system-success",
            "Demo System",
            "Tour Complete! You successfully navigated the basic incident flow. Feel free to close the Debrief or use the 'Close Demo' button again."
          ),
        300
      );
    });
    tour.on("cancel", () => {
      Logger.info("[Tour] Tour cancelled!");
      if (demoState !== "ENDED" && playerInput) {
        playerInput.disabled = false;
        if (playerInputForm) playerInputForm.classList.remove("disabled");
        playerInput.focus();
        addMessage(
          "system-info",
          "Demo System",
          "Tour cancelled. You can continue interacting or restart the tour."
        );
      }
      lastSubmittedCommandForTour = "";
    });
  } // End of initializeTour

  // --- 7. Initialization and Control --- (Refactored console calls)

  function resetDemoUI() {
    Logger.info("----- RESETTING DEMO UI -----");
    stopSimTimer();
    if (tour && tour.isActive()) tour.cancel();
    agentCurrentlyInConversation = null;
    currentSystemStatus = {};
    currentAgentStatus = {};
    currentMissedCalls = [];
    currentlyFocusedPanel = null;
    lastSubmittedCommandForTour = "";
    demoState = "IDLE";
    if (messageDisplay) messageDisplay.innerHTML = "";
    if (systemStatusList) systemStatusList.innerHTML = "";
    if (agentStatusList) agentStatusList.innerHTML = "";
    if (missedCallsList) missedCallsList.innerHTML = "";
    if (missedCallsSection) missedCallsSection.classList.add("hidden");
    if (logFeedList) logFeedList.innerHTML = "";
    hideInteractionContainers();
    hideDebriefModal();
    if (currentlyFocusedPanel) defocusPanel();
    if (focusModeControls) focusModeControls.classList.add("hidden");
    document.body.classList.remove("panel-is-focused");
    demoPlayerName = "You (CISO)";
    if (simHeaderTitle) simHeaderTitle.textContent = "Ransomware Demo";
    if (simPlayerInfo) simPlayerInfo.textContent = `${demoPlayerName}`;
    if (simIntensity) simIntensity.textContent = "1.0x";
    localSimTime = new Date();
    localSimTime.setMinutes(localSimTime.getMinutes() - 5);
    const endTime = new Date(localSimTime.getTime() + 30 * 60 * 1000);
    if (simTimeClock) simTimeClock.textContent = formatTimeLocal(localSimTime);
    if (simEndTime) simEndTime.textContent = formatTimeLocal(endTime);
    startSimTimer();
    updateSystemStatusUI({
      Website_Public: "NOMINAL",
      Customer_Database: "UNKNOWN",
      Auth_System: "UNKNOWN",
      Network_Segment_Gamma7: "UNKNOWN",
      Network_Segment_Internal: "UNKNOWN",
      File_Servers: "UNKNOWN",
      VPN_Access: "NOMINAL",
    });
    // Update initial agent statuses with new names
    updateAgentStatusUI({
      JAMES_BENNETT: "available", // Updated Name
      LAURA: "available", // Updated Name
      ETHAN_KIM: "available", // Updated Name
      CEO: "available",
      "Legal Counsel": "available",
      "PR Head": "available",
    });
    updateMissedCallsUI([]);
    addMessage(
      "system-info",
      "Demo System",
      `Welcome, ${demoPlayerName}. Interactive demo ready. Click 'Start Guided Tutorial' or 'Start Tour'.`
    );
    triggerDemoLogEntry({
      severity: "INFO",
      source: "Demo",
      message: "Interactive demo initialized.",
    });
    setSimStatus("Running", "running");
    demoState = "IDLE";
    Logger.info(`demoState reset to IDLE.`);
    if (playerInput) playerInput.disabled = false;
    if (playerInputForm) playerInputForm.classList.remove("disabled");
    if (playerInput) {
      playerInput.placeholder = "Enter command...";
      playerInput.focus();
    }
    Logger.info("----- DEMO UI RESET COMPLETE -----");
  }

  // --- 8. UI Event Listeners --- (Refactored console calls)
  panelToggleButtons.forEach((button) =>
    button.addEventListener("click", () => {
      const panel = button.closest(".status-panel");
      const iconSpan = button.querySelector(".toggle-icon");
      if (!panel || !iconSpan) return;
      const isMinimized = panel.classList.toggle("panel-minimized");
      iconSpan.textContent = isMinimized ? "+" : "-";
      button.setAttribute("aria-expanded", String(!isMinimized));
      const headerH4 = panel.querySelector(".panel-header h4");
      if (headerH4)
        headerH4.style.borderBottomColor = isMinimized ? "transparent" : "";
    })
  );
  allFocusButtons.forEach((button) =>
    button.addEventListener("click", () => {
      const panelToFocus = button.closest(".status-panel");
      if (panelToFocus) focusPanel(panelToFocus);
    })
  );
  if (defocusPanelBtn) defocusPanelBtn.addEventListener("click", defocusPanel);
  if (commandHelperBtn && commandDropdown) {
    commandHelperBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const isHidden = commandDropdown.classList.toggle("hidden");
      commandHelperBtn.setAttribute("aria-expanded", String(!isHidden));
    });
    commandDropdown.addEventListener("click", (event) => {
      if (event.target.classList.contains("command-item")) {
        const command = event.target.dataset.command;
        if (command && playerInput) {
          // Updated command generation for specific agents if needed
          let commandText = command;
          if (command === "call JAMES_BENNETT")
            commandText = "call JAMES_BENNETT";
          else if (command === "call LAURA") commandText = "call LAURA";
          else if (command === "call ETHAN_KIM") commandText = "call ETHAN_KIM";
          else if (command === "call CEO") commandText = "call CEO";
          else if (command === "call Legal Counsel")
            commandText = "call Legal Counsel";
          else if (command === "call PR Head") commandText = "call PR Head";
          else if (
            ["isolate", "block ip"].some((cmd) => command.startsWith(cmd))
          )
            commandText = command + " ";

          playerInput.value = commandText;
          playerInput.focus();
          commandDropdown.classList.add("hidden");
          commandHelperBtn.setAttribute("aria-expanded", "false");
        }
      }
    });
    document.addEventListener("click", (event) => {
      if (
        !commandDropdown.classList.contains("hidden") &&
        !commandDropdown.contains(event.target) &&
        !commandHelperBtn.contains(event.target)
      ) {
        commandDropdown.classList.add("hidden");
        commandHelperBtn.setAttribute("aria-expanded", "false");
      }
    });
  }
  if (playerInputForm && playerInput) {
    playerInputForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const command = playerInput.value.trim();
      Logger.debug(
        `Form submitted. Command: "${command}". Disabled: ${playerInput.disabled}`
      );
      if (!command || playerInput.disabled) return;
      lastSubmittedCommandForTour = command;
      processDemoPlayerInput(command);
      playerInput.value = "";
    });
  }
  if (submitBriefingButton && analystBriefingInput) {
    const handleBriefingSubmit = () => {
      Logger.debug("Briefing submit triggered.");
      if (demoState !== "SHOWING_BRIEFING") return;
      const points = analystBriefingInput.value.trim();
      if (!points) return;
      lastSubmittedCommandForTour = points;
      processDemoPlayerInput(points);
      analystBriefingInput.value = "";
    };
    submitBriefingButton.addEventListener("click", handleBriefingSubmit);
    analystBriefingInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleBriefingSubmit();
      }
    });
  }
  if (closeDebriefButton)
    closeDebriefButton.addEventListener("click", hideDebriefModal);
  if (debriefModal)
    debriefModal.addEventListener("click", (e) => {
      if (e.target === debriefModal) hideDebriefModal();
    });

  // --- 9. Focus/Defocus Panel Logic --- (Refactored console calls)
  function focusPanel(panelElement) {
    Logger.debug("focusPanel called", { panelId: panelElement?.id });
    if (
      !panelElement ||
      !mainColumn ||
      !messageDisplay ||
      !playerInputForm ||
      !focusModeControls
    ) {
      Logger.error("focusPanel missing required elements.");
      return;
    }
    if (currentlyFocusedPanel && currentlyFocusedPanel !== panelElement)
      defocusPanel();
    messageDisplay.classList.add("hidden");
    playerInputForm.classList.add("hidden");
    hideInteractionContainers();
    if (!panelElement.dataset.originalParentSelector) {
      const parent = panelElement.parentElement;
      panelElement.dataset.originalParentSelector = parent?.id
        ? `#${parent.id}`
        : ".sim-column-side";
    }
    originalPanelParent = panelElement.parentElement || sideColumn;
    mainColumn.appendChild(panelElement);
    panelElement.classList.add("is-focused-main");
    currentlyFocusedPanel = panelElement;
    focusModeControls.classList.remove("hidden");
    document.body.classList.add("panel-is-focused");
  }
  function defocusPanel() {
    Logger.debug("defocusPanel called", {
      currentPanel: currentlyFocusedPanel?.id,
    });
    if (
      !currentlyFocusedPanel ||
      !messageDisplay ||
      !playerInputForm ||
      !focusModeControls
    ) {
      Logger.warn(
        "defocusPanel called but no panel is focused or elements missing."
      );
      return;
    }
    const originalParentSelector =
      currentlyFocusedPanel.dataset.originalParentSelector ||
      ".sim-column-side";
    const parentElement =
      document.querySelector(originalParentSelector) || sideColumn;
    try {
      parentElement.appendChild(currentlyFocusedPanel);
    } catch (error) {
      Logger.error(
        "Error appending focused panel back to original parent:",
        { error: error },
        "Appending to side column as fallback."
      );
      sideColumn.appendChild(currentlyFocusedPanel);
    }
    currentlyFocusedPanel.classList.remove("is-focused-main");
    delete currentlyFocusedPanel.dataset.originalParentSelector;
    messageDisplay.classList.remove("hidden");
    playerInputForm.classList.remove("hidden");
    if (demoState === "SHOWING_DECISION" && decisionPointContainer)
      decisionPointContainer.classList.remove("hidden");
    else if (demoState === "SHOWING_YESNO" && yesNoPromptContainer)
      yesNoPromptContainer.classList.remove("hidden");
    else if (demoState === "SHOWING_BRIEFING" && analystBriefingContainer)
      analystBriefingContainer.classList.remove("hidden");
    focusModeControls.classList.add("hidden");
    document.body.classList.remove("panel-is-focused");
    currentlyFocusedPanel = null;
    originalPanelParent = sideColumn;
  }

  // --- 10. Initial Setup & Button Listeners --- (Refactored console calls)
  if (startTourBtn) {
    startTourBtn.addEventListener("click", () => {
      Logger.info("Start Tour button clicked (manual start/restart).");
      resetDemoUI();
      setTimeout(() => {
        if (tour) {
          if (tour.isActive()) {
            Logger.debug("Tour already active, cancelling and restarting.");
            tour.cancel();
            // Re-initialize needed if tour object state gets messy on cancel/restart
            initializeTour();
            setTimeout(() => tour.start(), 100);
          } else {
            Logger.debug("Starting Shepherd tour via Start Tour button...");
            initializeTour(); // Ensure tour is fresh
            tour.start();
          }
        } else {
          Logger.error("Tour object not initialized when Start Tour clicked.");
          initializeTour();
          if (tour) setTimeout(() => tour.start(), 100);
        }
      }, 150);
    });
  } else
    Logger.error("Original Start Tour button (#start-tour-btn) not found!");

  initializeTour(); // Define tour steps initially
  resetDemoUI(); // Set initial UI state

  if (startTutorialButton && promptOverlay && closeDemoButton) {
    Logger.debug("Attaching listener to Start Guided Tutorial button.");
    startTutorialButton.addEventListener("click", () => {
      Logger.info("Start Guided Tutorial button clicked.");
      if (promptOverlay) promptOverlay.classList.add("hidden");
      if (closeDemoButton) closeDemoButton.classList.add("visible");
      if (tour && typeof tour.start === "function") {
        // Ensure tour is reset and initialized before starting
        if (tour.isActive()) {
          Logger.debug(
            "Tutorial button: Tour was active, cancelling before restart."
          );
          tour.cancel();
        }
        initializeTour(); // Re-initialize to ensure clean state for tutorial start

        setTimeout(() => {
          Logger.info(
            "Starting Shepherd tour automatically via Tutorial button..."
          );
          tour.start(); // Start the freshly initialized tour
        }, 450);
      } else {
        Logger.error(
          "Error: Shepherd tour instance ('tour') not found or unusable when Tutorial button clicked."
        );
        // Attempt recovery
        initializeTour();
        if (tour) {
          setTimeout(() => tour.start(), 450);
        } else {
          alert(
            "Could not start the guided tour automatically. Please try the 'Start Tour' button."
          );
        }
      }
    });
  } else
    Logger.error(
      "Initialization Error: Could not find elements required for the initial prompt interaction:",
      { promptOverlay, startTutorialButton, closeDemoButton }
    );

  if (setupScreen) setupScreen.classList.remove("active");
  if (simulationInterface) simulationInterface.classList.add("active");
  Logger.info(
    "Interactive Demo UI Initialized. Ready for interaction or tour start."
  );
}); // End DOMContentLoaded
