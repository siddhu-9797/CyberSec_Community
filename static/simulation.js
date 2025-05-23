document.addEventListener("DOMContentLoaded", () => {
  const setupScreen = document.getElementById("setup-screen");
  const simulationInterface = document.getElementById("simulation-interface");
  const scenarioSelect = document.getElementById("scenario-select");
  const intensitySelect = document.getElementById("intensity-select");
  const durationSelect = document.getElementById("duration-select");
  const startSimButton = document.getElementById("start-sim-button");
  const setupError = document.getElementById("setup-error");
  const ORG_CHART_URL = "http://localhost:3000/";
  const simHeaderTitle = document.getElementById("sim-scenario-title");
  const simPlayerInfo = document.getElementById("sim-player-info");
  const simTimeClock = document.getElementById("sim-time-clock");
  const simEndTime = document.getElementById("sim-end-time");
  const simIntensity = document.getElementById("sim-intensity");
  const simStatusIndicator = document.getElementById("sim-status-indicator");
  const simStatusText = document.getElementById("sim-status-text");
  const exitSimBtn = document.getElementById("exit-sim-btn");
  const messageDisplay = document.getElementById("message-display");
  const playerInputForm = document.getElementById("player-input-form");
  const playerInput = document.getElementById("player-input");
  const submitButton = playerInputForm?.querySelector('button[type="submit"]');
  const userFeedbackSection = document.getElementById("user-feedback-rating");
  const starRatingContainer = userFeedbackSection?.querySelector(
    ".star-rating-container"
  );
  const starButtons = userFeedbackSection?.querySelectorAll(".star-btn");
  const feedbackInputContainer = document.getElementById(
    "feedback-input-container"
  );
  const feedbackTextarea = document.getElementById("feedback-text");
  const submitRatingButton = document.getElementById("submit-rating-btn");
  const ratingSubmitStatus = document.getElementById("rating-submit-status");
  const starOutlineTemplate = document.getElementById("star-outline-svg");
  const starFilledTemplate = document.getElementById("star-filled-svg");
  const wordCountDisplay = document.getElementById("player-input-word-count");
  const errorDisplay = document.getElementById("player-input-error");
  const errorContainer = document.getElementById("error-container");
  const MAX_CHARS = 100;

  const systemStatusPanel = document.getElementById("system-status-panel");
  const agentStatusPanel = document.getElementById("agent-status-panel");
  const logFeedPanel = document.getElementById("log-feed-panel");

  const systemStatusList = document.getElementById("system-status-list");
  const agentStatusList = document.getElementById("agent-status-list");
  const missedCallsSection = document.getElementById("missed-calls-section");
  const missedCallsList = document.getElementById("missed-calls-list");
  const logFeedList = document.querySelector(".log-feed-list");
  const sideColumn = document.querySelector(".sim-column-side");

  const defocusPanelBtn = document.getElementById("defocus-panel-btn");
  const focusModeControls = document.getElementById("focus-mode-controls");
  const mainColumn = document.querySelector(".sim-column-main");
  const MOBILE_BREAKPOINT_PX = 992;
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

  const systemStatusItemTemplate = document.getElementById(
    "system-status-item-template"
  );
  const agentStatusItemTemplate = document.getElementById(
    "agent-status-item-template"
  );
  const logFeedItemTemplate = document.getElementById("log-feed-item-template");
  const messageTemplate = document.getElementById("message-template");

  const showOrgChartBtn = document.getElementById("show-org-chart-btn");
  const iframeModal = document.getElementById("iframe-modal");
  const iframeModalBody = document.getElementById("iframe-modal-body");
  const iframeModalTitle = document.getElementById("iframe-modal-title");
  const closeIframeModalButton = document.getElementById("close-iframe-modal");

  let currentSimState = "SETUP";
  let activeAgentCallButtons = {};
  let socket = null;
  let currentSimulationId = null;
  let currentAuthToken = null;
  let currentSelectedRating = 0;
  let ratingApiEndpoint = "/sim/rate";
  let wsRetryCount = 0;
  const MAX_WS_RETRIES = 4;
  const WS_RETRY_DELAY = 1500;
  let pendingRatingUpdatePayload = null;
  let agentCurrentlyInConversation = null;
  let currentlyFocusedPanel = null;
  let originalPanelParent = sideColumn;
  let lastPlayerActionSent = null;
  let pendingYesNoPayload = null;
  let localSimTime = null;
  let simTimerIntervalId = null;
  let isSidebarHiddenBySwipe = false;
  let touchStartY = 0;
  let touchMoveY = 0;
  let touchStartTime = 0;
  const MIN_SWIPE_DISTANCE_Y = 50;
  const MAX_SWIPE_TIME = 500;
  const SIM_TIMER_INTERVAL_MS = 1000;
  const SESSION_STORAGE_DEMO_FLAG = "hasViewedDemoThisSession";
  const SESSION_STORAGE_PENDING_CONFIG = "pendingGuestSimConfig";
  const SESSION_STORAGE_ACTIVE_SIM = "activeSimulationId";
  const API_BASE_URL = "/api";

  function validatePlayerInput() {
    if (
      !playerInput ||
      !wordCountDisplay ||
      !errorContainer ||
      !errorDisplay ||
      !submitButton
    ) {
      return true;
    }

    const currentText = playerInput.value;
    const charCount = currentText.length;
    let isInputValid = true;

    wordCountDisplay.textContent = `${charCount} / ${MAX_CHARS} characters`;

    if (charCount > MAX_CHARS) {
      errorDisplay.textContent = `Exceeds max character limit (${MAX_CHARS})`;
      playerInput.classList.add("input-error");
      wordCountDisplay.classList.add("error");
      errorContainer.classList.add("active");
      submitButton.disabled = true;
      isInputValid = false;
    } else {
      errorDisplay.textContent = "";
      playerInput.classList.remove("input-error");
      wordCountDisplay.classList.remove("error");
      errorContainer.classList.remove("active");
      submitButton.disabled =
        currentText.trim().length === 0 || playerInput.disabled;
    }
    return isInputValid;
  }

  async function apiCall(
    endpoint,
    method = "GET",
    body = null,
    includeAuth = false
  ) {
    const options = {
      method: method,
      headers: { "Content-Type": "application/json" },
    };
    if (body) {
      options.body = JSON.stringify(body);
    }
    if (includeAuth && currentAuthToken) {
      options.headers["Authorization"] = `Bearer ${currentAuthToken}`;
    } else if (includeAuth && !currentAuthToken) {
    }
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
      if (!response.ok) {
        let errorData = { error: `HTTP error! status: ${response.status}` };
        try {
          errorData = await response.json();
        } catch (e) {}

        addMessage(
          "system-error",
          "System",
          `Backend Error (${response.status}): ${
            errorData.detail || errorData.error || response.statusText
          }`
        );
        if (endpoint === "/sim/start" || endpoint === "/sim/start_guest") {
          if (startSimButton) {
            startSimButton.disabled = false;
            startSimButton.textContent = "Initialize Pressure Chamber";
          }
          if (setupError)
            setupError.textContent = `Failed to start (${response.status}): ${
              errorData.detail || errorData.error || response.statusText
            }`;
        }
        return null;
      }
      if (response.status === 204) return {};
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json"))
        return await response.json();
      else
        return {
          success: true,
          status: response.status,
          text: await response.text(),
        };
    } catch (error) {
      addMessage(
        "system-error",
        "System",
        `Network Error contacting ${endpoint}. Check connection or backend status.`
      );
      if (endpoint === "/sim/start" || endpoint === "/sim/start_guest") {
        if (startSimButton) {
          startSimButton.disabled = false;
          startSimButton.textContent = "Initialize Pressure Chamber";
        }
        if (setupError)
          setupError.textContent = `Network error: ${error.message}`;
      }
      return null;
    }
  }

  function clearSimulationUI() {
    if (messageDisplay) messageDisplay.innerHTML = "";
    if (logFeedList) logFeedList.innerHTML = "";
    if (systemStatusList) systemStatusList.innerHTML = "";
    if (agentStatusList) agentStatusList.innerHTML = "";
    if (missedCallsList) missedCallsList.innerHTML = "";
    if (missedCallsSection) missedCallsSection.classList.add("hidden");
    hideInteractionContainers();
    hideDebriefModal();
    if (iframeModal && iframeModal.classList.contains("active")) {
      closeMainOrgChartModal();
    }
    if (simHeaderTitle) simHeaderTitle.textContent = "Scenario";
    if (simPlayerInfo) simPlayerInfo.textContent = "";
    if (simTimeClock) simTimeClock.textContent = "00:00:00";
    if (simEndTime) simEndTime.textContent = "00:00:00";
    if (simIntensity) simIntensity.textContent = "?.?x";
    setSimStatus("Setup");

    if (playerInput) {
      playerInput.value = "";
      playerInput.disabled = true;
    }
    if (playerInputForm) playerInputForm.classList.add("disabled");
    validatePlayerInput();
  }

  function handleBeforeUnload(event) {
    const activeSimStates = [
      "RUNNING",
      "AWAITING_PLAYER_CHOICE",
      "IN_CONVERSATION",
      "AGENT_PROCESSING",
      "DECISION_POINT_SHUTDOWN",
      "AWAITING_ANALYST_BRIEFING",
      "POST_INITIAL_CRISIS",
    ];

    if (activeSimStates.includes(currentSimState)) {
      Logger.info(
        "BeforeUnload: Simulation active, triggering browser prompt."
      );
      event.preventDefault();
      event.returnValue = "";
    } else {
      Logger.info(
        `BeforeUnload: State is ${currentSimState}, allowing unload.`
      );
    }
  }
  function initializeUserRatingUI() {
    if (!starButtons || !starOutlineTemplate) return;
    currentSelectedRating = 0;
    starButtons.forEach((btn) => {
      btn.innerHTML = starOutlineTemplate.innerHTML;
      btn.classList.remove("selected");
    });
    if (feedbackInputContainer)
      feedbackInputContainer.classList.remove("visible");
    if (feedbackTextarea) feedbackTextarea.value = "";
    if (submitRatingButton) submitRatingButton.disabled = true;
    if (ratingSubmitStatus) ratingSubmitStatus.textContent = "";
    if (userFeedbackSection) userFeedbackSection.style.display = "";
  }

  function handleStarClick(event) {
    const button = event.currentTarget;
    const rating = parseInt(button.dataset.rating || "0");
    if (
      rating === 0 ||
      !starButtons ||
      !starOutlineTemplate ||
      !starFilledTemplate
    )
      return;

    Logger.info(`Star clicked: Rating ${rating}`);
    currentSelectedRating = rating;

    starButtons.forEach((btn) => {
      const btnRating = parseInt(btn.dataset.rating || "0");
      if (btnRating <= rating) {
        btn.innerHTML = starFilledTemplate.innerHTML;
        btn.classList.add("selected");
      } else {
        btn.innerHTML = starOutlineTemplate.innerHTML;
        btn.classList.remove("selected");
      }
    });

    if (rating <= 3) {
      if (feedbackInputContainer)
        feedbackInputContainer.classList.add("visible");
    } else {
      if (feedbackInputContainer)
        feedbackInputContainer.classList.remove("visible");
    }

    if (submitRatingButton) submitRatingButton.disabled = false;
    if (ratingSubmitStatus) ratingSubmitStatus.textContent = "";
  }

  async function handleSubmitRating() {
    if (currentSelectedRating === 0 || !submitRatingButton) return;

    Logger.info(`Submitting rating: ${currentSelectedRating}`);
    submitRatingButton.disabled = true;
    if (ratingSubmitStatus) {
      ratingSubmitStatus.textContent = "Submitting...";
      ratingSubmitStatus.classList.remove("error");
    }

    const feedback =
      feedbackInputContainer &&
      feedbackInputContainer.classList.contains("visible") &&
      feedbackTextarea
        ? feedbackTextarea.value.trim()
        : null;

    const payload = {
      simulation_id: currentSimulationId || "UNKNOWN_SIM_ID_FOR_RATING",
      rating: currentSelectedRating,
      feedback: feedback,
    };
    const response = await apiCall(ratingApiEndpoint, "POST", payload, false);
    if (
      response &&
      (response.message === "Thank you for your feedback!" || response.success)
    ) {
      Logger.info("Rating submitted successfully.");
      if (ratingSubmitStatus)
        ratingSubmitStatus.textContent = "Thank you for your feedback!";
      if (userFeedbackSection) {
      }
    } else {
      Logger.error("Failed to submit rating.");
      if (ratingSubmitStatus) {
        ratingSubmitStatus.textContent =
          "Error submitting feedback. Please try again.";
        ratingSubmitStatus.classList.add("error");
      }
      if (submitRatingButton) submitRatingButton.disabled = false;
    }
  }
  function handleExitSimulation() {
    if (
      !confirm(
        "Are you sure you want to exit the current simulation? Your progress will be lost."
      )
    ) {
      return;
    }

    Logger.info("User initiated simulation exit.");

    stopSimTimer();
    closeWebSocket();

    const simIdBeforeExit = currentSimulationId;
    currentSimulationId = null;
    currentAuthToken = null;
    currentSimState = "SETUP";
    agentCurrentlyInConversation = null;
    activeAgentCallButtons = {};
    pendingRatingUpdatePayload = null;
    pendingYesNoPayload = null;
    lastPlayerActionSent = null;
    currentlyFocusedPanel = null;
    document.body.classList.remove("panel-is-focused");

    clearSimulationUI();

    if (simulationInterface) simulationInterface.classList.remove("active");
    if (setupScreen) setupScreen.classList.add("active");
  }
  function openMainOrgChartModal() {
    if (!iframeModal || !iframeModalBody) {
      Logger.error("Cannot open org chart: Modal DOM elements not found.");

      return;
    }
    if (!ORG_CHART_URL) {
      Logger.error("Cannot open org chart: ORG_CHART_URL is not defined.");

      return;
    }

    Logger.info(`Opening main org chart modal for URL: ${ORG_CHART_URL}`);

    if (iframeModalTitle) iframeModalTitle.textContent = "Organization Chart";

    iframeModalBody.innerHTML = `
            <iframe
               src="${ORG_CHART_URL}"
               frameborder="0"
               title="Organization Chart"
               style="width: 100%; height: 100%; border: none; display: block;">
            </iframe>`;

    iframeModal.classList.add("active");
    document.body.style.overflow = "hidden";

    if (closeIframeModalButton) closeIframeModalButton.focus();
  }

  function closeMainOrgChartModal() {
    if (!iframeModal || !iframeModalBody) return;

    Logger.info("Closing main org chart modal.");

    iframeModal.classList.remove("active");
    document.body.style.overflow = "";

    iframeModalBody.innerHTML = "<p>Loading chart...</p>";
  }
  function handleTouchStart(event) {
    if (event.touches.length !== 1) return;
    touchStartY = event.touches[0].clientY;
    touchMoveY = touchStartY;
    touchStartTime = Date.now();
  }

  function handleTouchMove(event) {
    if (event.touches.length !== 1) return;
    touchMoveY = event.touches[0].clientY;
  }

  function handleTouchEnd(event) {
    const touchEndY = touchMoveY;
    const deltaY = touchEndY - touchStartY;
    const elapsedTime = Date.now() - touchStartTime;

    if (
      Math.abs(deltaY) >= MIN_SWIPE_DISTANCE_Y &&
      elapsedTime <= MAX_SWIPE_TIME
    ) {
      if (deltaY > 0) {
        hideSidebarOnMobile();
      } else {
        showSidebarOnMobile();
      }
    }
    touchStartY = 0;
    touchMoveY = 0;
    touchStartTime = 0;
  }

  function hideSidebarOnMobile() {
    if (
      sideColumn &&
      !isSidebarHiddenBySwipe &&
      window.innerWidth <= MOBILE_BREAKPOINT_PX
    ) {
      Logger.info("Swipe Down: Hiding sidebar.");

      sideColumn.classList.add("swiped-hidden");
      isSidebarHiddenBySwipe = true;
    }
  }

  function showSidebarOnMobile() {
    if (
      sideColumn &&
      isSidebarHiddenBySwipe &&
      window.innerWidth <= MOBILE_BREAKPOINT_PX
    ) {
      Logger.info("Swipe Up: Showing sidebar.");

      sideColumn.classList.remove("swiped-hidden");
      isSidebarHiddenBySwipe = false;
    }
  }

  let swipeListenersActive = false;

  function manageSwipeListeners() {
    const shouldBeActive = window.innerWidth <= MOBILE_BREAKPOINT_PX;

    if (shouldBeActive && !swipeListenersActive && mainColumn) {
      mainColumn.addEventListener("touchstart", handleTouchStart, {
        passive: true,
      });
      mainColumn.addEventListener("touchmove", handleTouchMove, {
        passive: true,
      });
      mainColumn.addEventListener("touchend", handleTouchEnd);
      mainColumn.addEventListener("touchcancel", handleTouchEnd);
      swipeListenersActive = true;
      Logger.info("Swipe listeners attached for mobile.");
    } else if (!shouldBeActive && swipeListenersActive && mainColumn) {
      mainColumn.removeEventListener("touchstart", handleTouchStart);
      mainColumn.removeEventListener("touchmove", handleTouchMove);
      mainColumn.removeEventListener("touchend", handleTouchEnd);
      mainColumn.removeEventListener("touchcancel", handleTouchEnd);
      swipeListenersActive = false;
      if (sideColumn) sideColumn.classList.remove("swiped-hidden");
      isSidebarHiddenBySwipe = false;
      Logger.info("Swipe listeners removed for desktop.");
    }
  }

  let resizeTimeout;
  function handleResize() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      manageSwipeListeners();
    }, 250);
  }

  function checkAndStartPendingSimulation() {
    const pendingSimId = sessionStorage.getItem(SESSION_STORAGE_ACTIVE_SIM);
    if (pendingSimId) {
      sessionStorage.removeItem(SESSION_STORAGE_ACTIVE_SIM);
      currentSimulationId = pendingSimId;
      currentAuthToken = null;
      if (setupScreen) setupScreen.classList.remove("active");
      if (simulationInterface) simulationInterface.classList.add("active");
      const connectDelayMs = 1500;
      addMessage(
        "system-info",
        "System",
        `Connecting to simulation ${pendingSimId.slice(-8)}...`
      );
      setSimStatus("Connecting WS", "paused");
      setTimeout(() => {
        initializeWebSocket(currentSimulationId, null);
        validatePlayerInput();
      }, connectDelayMs);
      return true;
    }
    return false;
  }
  function stopSimTimer() {
    if (simTimerIntervalId) {
      clearInterval(simTimerIntervalId);
      simTimerIntervalId = null;
    }
  }
  function startSimTimer() {
    stopSimTimer();
    if (!localSimTime || isNaN(localSimTime.getTime())) {
      return;
    }
    simTimerIntervalId = setInterval(() => {
      if (!localSimTime || isNaN(localSimTime.getTime())) {
        stopSimTimer();
        return;
      }
      localSimTime.setSeconds(localSimTime.getSeconds() + 1);
      if (simTimeClock) {
        simTimeClock.textContent = formatTimeLocal(localSimTime.toISOString());
      }
    }, SIM_TIMER_INTERVAL_MS);
  }
  function formatTimeLocal(isoString) {
    if (!isoString) {
      return "--:--:--";
    }
    try {
      const dateObj = new Date(isoString);
      if (isNaN(dateObj.getTime())) {
        return "??:??:??";
      }
      const options = {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      };
      return dateObj.toLocaleTimeString(navigator.language, options);
    } catch (e) {
      return "??:??:??";
    }
  }

  function focusPanel(panelElement) {
    if (
      !panelElement ||
      !mainColumn ||
      !messageDisplay ||
      !playerInputForm ||
      !focusModeControls
    )
      return;
    messageDisplay.classList.add("hidden");
    playerInputForm.classList.add("hidden");
    if (decisionPointContainer) decisionPointContainer.classList.add("hidden");
    if (analystBriefingContainer)
      analystBriefingContainer.classList.add("hidden");
    if (yesNoPromptContainer) yesNoPromptContainer.classList.add("hidden");
    if (!panelElement.dataset.originalParent) {
      panelElement.dataset.originalParent = ".sim-column-side";
    }
    originalPanelParent = panelElement.parentElement;
    mainColumn.appendChild(panelElement);
    panelElement.classList.add("is-focused-main");
    currentlyFocusedPanel = panelElement;
    focusModeControls.classList.remove("hidden");
    document.body.classList.add("panel-is-focused");
  }
  function defocusPanel() {
    if (
      !currentlyFocusedPanel ||
      !originalPanelParent ||
      !messageDisplay ||
      !playerInputForm ||
      !focusModeControls
    )
      return;
    originalPanelParent.appendChild(currentlyFocusedPanel);
    currentlyFocusedPanel.classList.remove("is-focused-main");
    messageDisplay.classList.remove("hidden");
    playerInputForm.classList.remove("hidden");
    focusModeControls.classList.add("hidden");
    document.body.classList.remove("panel-is-focused");
    currentlyFocusedPanel = null;
  }

  async function sendPlayerAction(action) {
    if (!currentSimulationId) {
      addMessage(
        "system-error",
        "System",
        "Cannot send action: Simulation not properly initialized."
      );
      return;
    }
    const endpoint = `/sim/${currentSimulationId}/action`;
    const payload = { action_request: { action: action } };
    try {
      const response = await apiCall(
        endpoint,
        "POST",
        payload,
        !!currentAuthToken
      );
      if (!response) {
      }
    } catch (error) {
      addMessage(
        "system-error",
        "System Command",
        `Unexpected network error sending action '${action}'.`
      );
    }
  }

  function initializeWebSocket(simulationId, authToken, isRetry = false) {
    if (!isRetry) {
      wsRetryCount = 0;
    }
    if (
      socket &&
      (socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    currentSimulationId = simulationId;
    currentAuthToken = authToken;
    const wsProtocol =
      window.location.protocol === "https:" ? "wss://" : "ws://";
    let wsUrl = `${wsProtocol}${window.location.host}${API_BASE_URL}/sim/ws/${simulationId}`;
    if (authToken) {
      wsUrl += `?token=${encodeURIComponent(authToken)}`;
    }
    setSimStatus("Connecting WS", "paused");
    try {
      socket = new WebSocket(wsUrl);
      socket.onopen = (event) => {
        wsRetryCount = 0;
      };
      socket.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data);
          handleSimulationEvent(eventData);
        } catch (e) {}
      };
      socket.onerror = (error) => {};
      socket.onclose = (event) => {
        socket = null;
        stopSimTimer();
        if (
          (event.code === 1006 || !event.wasClean) &&
          wsRetryCount < MAX_WS_RETRIES &&
          currentSimState !== "ENDED"
        ) {
          wsRetryCount++;
          setSimStatus(`Connection Failed (Retrying ${wsRetryCount})`, "error");
          setTimeout(() => {
            initializeWebSocket(simulationId, authToken, true);
          }, WS_RETRY_DELAY);
        } else {
          if (currentSimState !== "ENDED") {
            setSimStatus(`Connection Failed (${event.code})`, "error");
            addMessage(
              "system-error",
              "WebSocket",
              `Connection failed permanently (${event.code}).`
            );
            if (playerInput) playerInput.disabled = true;
            if (playerInputForm) playerInputForm.classList.add("disabled");
            currentSimulationId = null;
            validatePlayerInput();
          } else {
            setSimStatus("Ended", "ended");
          }
        }
      };
    } catch (error) {
      setSimStatus("WS Creation Error", "error");
      addMessage(
        "system-error",
        "System",
        "Failed to initialize WebSocket connection."
      );
    }
  }
  function closeWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, "Client closing connection normally.");
    }
    socket = null;
    stopSimTimer();
  }

  function addMessage(
    type,
    speaker,
    text,
    notification = null,
    actionButtons = null
  ) {
    if (!messageTemplate || !messageDisplay) {
      return;
    }
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
      return;
    }
    messageDiv.classList.add(type);
    if (speaker) {
      speakerSpan.textContent = `${speaker}:`;
    } else {
      speakerSpan.remove();
    }
    textP.textContent = text;
    if (notification) {
      notificationDiv.textContent = `** ${notification} **`;
    } else {
      notificationDiv.remove();
    }
    if (
      actionButtons &&
      Array.isArray(actionButtons) &&
      actionButtons.length > 0
    ) {
      messageActionsDiv.innerHTML = "";
      actionButtons.forEach((buttonConfig) => {
        if (!buttonConfig || !buttonConfig.text || !buttonConfig.command) {
          return;
        }
        const button = document.createElement("button");
        button.textContent = buttonConfig.text;
        button.classList.add("btn", ...(buttonConfig.classes || []));
        button.onclick = (event) => {
          event.stopPropagation();
          if (playerInput && playerInputForm && !playerInput.disabled) {
            const isValid = validatePlayerInput();
            if (!isValid) {
              addMessage(
                "system-warning",
                "System",
                "Cannot submit via button while input has error."
              );
              return;
            }
            playerInput.value = buttonConfig.command;
            playerInputForm.dispatchEvent(
              new Event("submit", { bubbles: true, cancelable: true })
            );
            messageActionsDiv.classList.add("hidden");
            messageActionsDiv.innerHTML = "";
          }
        };
        messageActionsDiv.appendChild(button);
      });
      messageActionsDiv.classList.remove("hidden");
    } else {
      messageActionsDiv.remove();
    }
    messageDisplay.insertBefore(messageDiv, messageDisplay.firstChild);
    messageDisplay.scrollTop = 0;
  }
  function updateSystemStatusUI(statusData) {
    if (!systemStatusList || !systemStatusItemTemplate) {
      return;
    }
    systemStatusList.innerHTML = "";
    const sortedKeys = Object.keys(statusData).sort();
    sortedKeys.forEach((key) => {
      const statusValue = statusData[key] || "UNKNOWN";
      const itemClone = systemStatusItemTemplate.content.cloneNode(true);
      const li = itemClone.querySelector("li");
      const keySpan = li.querySelector(".status-key");
      const valueSpan = li.querySelector(".status-value");
      const dotSpan = li.querySelector(".status-dot");
      if (!li || !keySpan || !valueSpan || !dotSpan) {
        return;
      }
      const baseStatus = statusValue.split(" ")[0].toUpperCase();
      li.dataset.systemKey = key;
      li.dataset.status = baseStatus;
      const readableKey = key.replace(/_/g, " ");
      const cleanedValue = statusValue.replace(/\(.*\)/g, "").trim();
      keySpan.textContent = readableKey;
      valueSpan.textContent = cleanedValue;
      systemStatusList.appendChild(li);
    });
  }
  function updateAgentStatusUI(agentStatusData) {
    if (!agentStatusList || !agentStatusItemTemplate) {
      return;
    }
    agentStatusList.innerHTML = "";
    activeAgentCallButtons = {};
    const sortedNames = Object.keys(agentStatusData).sort();
    sortedNames.forEach((name) => {
      const state = agentStatusData[name] || "unknown";
      const itemClone = agentStatusItemTemplate.content.cloneNode(true);
      const li = itemClone.querySelector("li");
      const nameSpan = li.querySelector(".agent-name");
      const valueSpan = li.querySelector(".status-value");
      const dotSpan = li.querySelector(".status-dot");
      const callButton = li.querySelector(".btn-agent-call");
      const endCallButton = li.querySelector(".btn-agent-end-call");
      const thinkingIndicator = li.querySelector(".agent-thinking-indicator");
      if (
        !li ||
        !nameSpan ||
        !valueSpan ||
        !dotSpan ||
        !callButton ||
        !endCallButton ||
        !thinkingIndicator
      ) {
        return;
      }
      li.dataset.agentName = name;
      li.dataset.state = state;
      const readableState = state.replace(/_/g, " ");
      nameSpan.textContent = name;
      valueSpan.textContent = readableState;
      callButton.onclick = () => handleAgentCallButton(name);
      endCallButton.onclick = () => handleEndCallButton(name);
      activeAgentCallButtons[name] = {
        button: callButton,
        endButton: endCallButton,
        indicator: thinkingIndicator,
        listItem: li,
      };
      if (name === agentCurrentlyInConversation) {
        callButton.classList.add("hidden");
        endCallButton.classList.remove("hidden");
      } else {
        callButton.classList.remove("hidden");
        endCallButton.classList.add("hidden");
      }
      agentStatusList.appendChild(li);
    });
  }
  function handleAgentCallButton(agentName) {
    if (
      currentSimState !== "IN_CONVERSATION" &&
      currentSimState !== "DECISION_POINT_SHUTDOWN" &&
      currentSimState !== "ENDED" &&
      !playerInput.disabled
    ) {
      const isValid = validatePlayerInput();
      if (!isValid) {
        addMessage(
          "system-warning",
          "System",
          "Cannot initiate call while input has error."
        );
        return;
      }
      playerInput.value = `call ${agentName}`;
      playerInputForm.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true })
      );
    } else {
      addMessage(
        "system",
        "System",
        `Cannot initiate call while in state: ${currentSimState} or input disabled.`
      );
    }
  }
  function handleEndCallButton(agentName) {
    if (
      currentSimState === "IN_CONVERSATION" &&
      agentName === agentCurrentlyInConversation &&
      !playerInput.disabled
    ) {
      const isValid = validatePlayerInput();
      if (!isValid) {
        addMessage(
          "system-warning",
          "System",
          "Cannot hang up while input has error."
        );
        return;
      }
      playerInput.value = "hang up";
      playerInputForm.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true })
      );
    } else {
    }
  }
  function updateMissedCallsUI(missedCalls) {
    if (!missedCallsSection || !missedCallsList) {
      return;
    }
    if (missedCalls && missedCalls.length > 0) {
      missedCallsList.innerHTML = "";
      missedCalls.forEach((name) => {
        const li = document.createElement("li");
        li.textContent = name;
        const returnCallBtn = document.createElement("button");
        returnCallBtn.textContent = "Call Back";
        returnCallBtn.classList.add("btn-return-call");
        returnCallBtn.onclick = () => {
          if (
            currentSimState !== "IN_CONVERSATION" &&
            currentSimState !== "DECISION_POINT_SHUTDOWN" &&
            !playerInput.disabled
          ) {
            const isValid = validatePlayerInput();
            if (!isValid) {
              addMessage(
                "system-warning",
                "System",
                "Cannot call back while input has error."
              );
              return;
            }
            playerInput.value = `call ${name}`;
            playerInputForm.dispatchEvent(
              new Event("submit", { bubbles: true, cancelable: true })
            );
          } else {
            addMessage(
              "system",
              "System",
              `Finish current interaction or wait until input enabled before calling back ${name}.`
            );
          }
        };
        li.appendChild(returnCallBtn);
        missedCallsList.appendChild(li);
      });
      missedCallsSection.classList.remove("hidden");
    } else {
      missedCallsSection.classList.add("hidden");
    }
  }
  function addLogFeedEntry(logData) {
    if (!logFeedList || !logFeedItemTemplate) {
      return;
    }
    const itemClone = logFeedItemTemplate.content.cloneNode(true);
    const li = itemClone.querySelector("li");
    const timeSpan = li.querySelector(".log-time");
    const severitySpan = li.querySelector(".log-severity");
    const sourceSpan = li.querySelector(".log-source");
    const messageSpan = li.querySelector(".log-message");
    if (!li || !timeSpan || !severitySpan || !sourceSpan || !messageSpan) {
      return;
    }
    const timestamp = logData.timestamp
      ? new Date(logData.timestamp).toLocaleTimeString()
      : "??:??:??";
    const severity = logData.severity || "INFO";
    const upperSeverity = severity.toUpperCase();
    const source = logData.source || "Unknown";
    const message = logData.message || "No message";
    li.classList.add(`severity-${upperSeverity}`);
    timeSpan.textContent = timestamp;
    severitySpan.textContent = severity;
    severitySpan.className = `log-severity ${upperSeverity}`;
    sourceSpan.textContent = source;
    messageSpan.textContent = message;
    logFeedList.insertBefore(li, logFeedList.firstChild);
    if (logFeedList.children.length > 150) {
      logFeedList.removeChild(logFeedList.lastChild);
    }
  }
  function showDecisionPoint(payload) {
    hideInteractionContainers();
    decisionTitle.textContent = payload.title || "Decision Required";
    decisionSummary.textContent = payload.summary || "";
    decisionOptions.innerHTML = "";
    if (payload.options && Array.isArray(payload.options)) {
      payload.options.forEach((opt) => {
        const button = document.createElement("button");
        button.textContent = opt.label;
        button.classList.add("btn", "btn-option");
        button.onclick = () => {
          const isValid = validatePlayerInput();
          if (!isValid) {
            addMessage(
              "system-warning",
              "System",
              "Cannot submit decision while input has error."
            );
            return;
          }
          playerInput.value = opt.value;
          playerInputForm.dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
          );
        };
        decisionOptions.appendChild(button);
      });
    }
    decisionPointContainer.classList.remove("hidden");
    playerInput.placeholder = "Enter your decision or click option.";
    playerInput.focus();
    validatePlayerInput();
  }
  function showYesNoPrompt(payload) {
    hideInteractionContainers();
    const promptText = payload.prompt || "Enter 'yes' or 'no':";
    yesNoPromptText.textContent = promptText;
    yesNoPromptContainer.dataset.actionContext = payload.action_context || "";
    yesNoPromptContainer.classList.remove("hidden");
    playerInput.placeholder = "Enter 'yes' or 'no'...";
    playerInput.focus();
    validatePlayerInput();
  }
  function showAnalystBriefingInput(payload) {
    hideInteractionContainers();
    const contextQuestion =
      payload.context_question || "Prepare briefing points:";
    analystBriefingContext.textContent = contextQuestion;
    analystBriefingInput.value = "";
    analystBriefingContainer.classList.remove("hidden");
    analystBriefingInput.focus();
    validatePlayerInput();
  }
  function hideInteractionContainers() {
    if (decisionPointContainer) decisionPointContainer.classList.add("hidden");
    if (analystBriefingContainer)
      analystBriefingContainer.classList.add("hidden");
    if (yesNoPromptContainer) yesNoPromptContainer.classList.add("hidden");
    if (playerInput) playerInput.placeholder = "Enter command...";
    validatePlayerInput();
  }

  function showDebriefModal(payload) {
    hideInteractionContainers();
    setSimStatus("Debriefing", "ended");

    if (debriefTitle) {
      debriefTitle.textContent = payload?.title || "-- Simulation Debrief --";
    } else {
      Logger.error("Debrief title element not found.");
      return;
    }
    if (!debriefModal) {
      Logger.error("Debrief modal element not found.");
      return;
    }

    if (debriefSummaryPoints) {
      debriefSummaryPoints.innerHTML = "";
      if (payload?.summary_points && Array.isArray(payload.summary_points)) {
        const summaryList = document.createElement("ul");
        payload.summary_points.forEach((point) => {
          const li = document.createElement("li");
          li.textContent = point;
          summaryList.appendChild(li);
        });
        const summaryHeading = document.createElement("h4");
        summaryHeading.textContent = "Summary";
        debriefSummaryPoints.appendChild(summaryHeading);
        debriefSummaryPoints.appendChild(summaryList);
      }
    }

    if (debriefFinalStatus) {
      debriefFinalStatus.innerHTML = "";
      if (payload?.final_status_report) {
        const statusPre = document.createElement("pre");
        statusPre.textContent = payload.final_status_report;
        const statusHeading = document.createElement("h4");
        statusHeading.textContent = "Final System Status";
        debriefFinalStatus.appendChild(statusHeading);
        debriefFinalStatus.appendChild(statusPre);
      }
    }

    if (
      debriefPerformanceRating &&
      ratingScores &&
      ratingFeedback &&
      ratingError
    ) {
      ratingScores.innerHTML = "";
      ratingFeedback.textContent = "";
      ratingError.textContent = "";

      if (payload?.performance_rating) {
        const rating = payload.performance_rating;
        const performanceHeading = document.createElement("h4");
        performanceHeading.textContent = "Performance Analysis";
        debriefPerformanceRating.innerHTML = "";
        debriefPerformanceRating.appendChild(performanceHeading);
        debriefPerformanceRating.appendChild(ratingScores);
        debriefPerformanceRating.appendChild(ratingFeedback);
        debriefPerformanceRating.appendChild(ratingError);

        if (rating.error) {
          ratingError.textContent = `Rating Error: ${rating.error}`;
          ratingFeedback.textContent = rating.raw_response
            ? `Raw Response: ${rating.raw_response}`
            : "";
        } else {
          const createScoreItem = (label, score) => {
            const item = document.createElement("div");
            item.classList.add("rating-score-item");
            const labelSpan = document.createElement("span");
            labelSpan.classList.add("rating-label");
            labelSpan.textContent = label;
            const valueSpan = document.createElement("span");
            valueSpan.classList.add("rating-value");
            const displayScore =
              score === null || score === undefined ? "?" : score;
            valueSpan.dataset.score = displayScore;
            valueSpan.innerHTML = `${displayScore} <span class="max-score">/ 10</span>`;
            item.appendChild(labelSpan);
            item.appendChild(valueSpan);
            return item;
          };

          ratingScores.appendChild(
            createScoreItem("Overall", rating.overall_score)
          );
          ratingScores.appendChild(
            createScoreItem("Timeliness", rating.timeliness_score)
          );
          ratingScores.appendChild(
            createScoreItem("Contact Strategy", rating.contact_strategy_score)
          );
          ratingScores.appendChild(
            createScoreItem("Decision Quality", rating.decision_quality_score)
          );
          ratingScores.appendChild(
            createScoreItem("Efficiency", rating.efficiency_score)
          );

          ratingFeedback.textContent =
            rating.qualitative_feedback || "No qualitative feedback provided.";
        }
      } else {
        const performanceHeading = document.createElement("h4");
        performanceHeading.textContent = "Performance Analysis";
        debriefPerformanceRating.innerHTML = "";
        debriefPerformanceRating.appendChild(performanceHeading);
        debriefPerformanceRating.appendChild(ratingError);
        ratingError.textContent = "Performance rating data not available.";
      }
    } else {
      Logger.warn("Debrief performance rating elements not found.");
    }

    if (userFeedbackSection && starButtons && submitRatingButton) {
      initializeUserRatingUI();

      starButtons.forEach((btn) =>
        btn.removeEventListener("click", handleStarClick)
      );
      submitRatingButton.removeEventListener("click", handleSubmitRating);

      starButtons.forEach((btn) =>
        btn.addEventListener("click", handleStarClick)
      );
      submitRatingButton.addEventListener("click", handleSubmitRating);
    } else {
      Logger.warn(
        "User feedback rating section elements not found in debrief modal."
      );
    }

    debriefModal.classList.add("active");
    document.body.style.overflow = "hidden";
    validatePlayerInput();

    const modalContent = debriefModal.querySelector(".sim-modal-content");
    if (modalContent) modalContent.scrollTop = 0;
  }
  function hideDebriefModal() {
    let willShowRatingUpdate = !!pendingRatingUpdatePayload;
    let willShowYesNo = !!pendingYesNoPayload;
    if (debriefModal && debriefModal.classList.contains("active")) {
      debriefModal.classList.remove("active");
      document.body.style.overflow = "";
    } else {
      return;
    }
    if (willShowRatingUpdate) {
      setTimeout(() => {
        if (!debriefModal || !debriefModal.classList.contains("active")) {
          showDebriefModal(pendingRatingUpdatePayload);
        }
        pendingRatingUpdatePayload = null;
      }, 150);
    } else if (willShowYesNo) {
      setTimeout(() => {
        if (!debriefModal || !debriefModal.classList.contains("active")) {
          showYesNoPrompt(pendingYesNoPayload);
          pendingYesNoPayload = null;
        }
      }, 150);
    } else {
      validatePlayerInput();
    }
  }
  function setSimStatus(statusText, cssClass = null) {
    if (simStatusText) simStatusText.textContent = statusText;
    let finalCssClass = cssClass;
    if (!finalCssClass) {
      const lowerText = statusText.toLowerCase();
      if (lowerText.includes("running")) finalCssClass = "running";
      else if (lowerText.includes("paused")) finalCssClass = "paused";
      else if (lowerText.includes("connecting")) finalCssClass = "paused";
      else if (lowerText.includes("ended")) finalCssClass = "ended";
      else if (lowerText.includes("debrief")) finalCssClass = "ended";
      else if (lowerText.includes("error")) finalCssClass = "error";
      else if (lowerText.includes("failed")) finalCssClass = "error";
      else finalCssClass = "";
    }
    if (simStatusIndicator)
      simStatusIndicator.className = `sim-status ${finalCssClass}`;
  }
  function showAgentThinking(agentName, isThinking) {
    const agentUI = activeAgentCallButtons[agentName];
    if (agentUI && agentUI.indicator) {
      agentUI.indicator.classList.toggle("hidden", !isThinking);
    }
  }

  function handleSimulationEvent(event) {
    if (!event || !event.type) {
      return;
    }
    const type = event.type;
    const payload = event.payload || {};
    switch (type) {
      case "initial_state":
        handleSimulationUiSetup(payload);
        setSimStatus("Running", "running");
        handleStateChange(payload.current_state || "AWAITING_PLAYER_CHOICE");
        break;
      case "log_feed_update":
        addLogFeedEntry(payload);
        break;
      case "state_change":
        {
          const oldState = currentSimState;
          handleStateChange(payload.new_state);
          if (
            oldState === "IN_CONVERSATION" &&
            currentSimState !== "IN_CONVERSATION" &&
            agentCurrentlyInConversation
          ) {
            const agentUI =
              activeAgentCallButtons[agentCurrentlyInConversation];
            if (agentUI) {
              agentUI.button.classList.remove("hidden");
              agentUI.endButton.classList.add("hidden");
              if (agentUI.indicator) agentUI.indicator.classList.add("hidden");
            }
            agentCurrentlyInConversation = null;
          }
        }
        break;
      case "time_update":
        {
          stopSimTimer();
          let backendTimeValid = false;
          if (payload.sim_time_iso) {
            try {
              const backendSimDate = new Date(payload.sim_time_iso);
              if (isNaN(backendSimDate.getTime()))
                throw new Error("Invalid Date");
              localSimTime = backendSimDate;
              backendTimeValid = true;
              if (simTimeClock) {
                simTimeClock.textContent = formatTimeLocal(
                  payload.sim_time_iso
                );
              }
            } catch (e) {
              localSimTime = null;
              if (simTimeClock) simTimeClock.textContent = "??:??:??";
            }
          } else {
            localSimTime = null;
            if (simTimeClock) simTimeClock.textContent = "??:??:??";
          }
          if (simEndTime && payload.end_time_iso) {
            simEndTime.textContent = formatTimeLocal(payload.end_time_iso);
          }
          if (backendTimeValid) {
            startSimTimer();
          }
        }
        break;

      case "request_user_rating":
        Logger.info("Backend requested user rating.", payload);
        // Ensure the debrief modal is visible
        if (debriefModal && !debriefModal.classList.contains("active")) {
          // If debrief modal wasn't shown yet (e.g. LLM rating still pending or errored)
          // show a minimal version of it or use pending data.
          showDebriefModal(
            pendingRatingUpdatePayload || { title: "-- Simulation Debrief --" }
          );
          pendingRatingUpdatePayload = null; // Clear if used
        }
        // Ensure the user rating section within the modal is visible and ready
        if (userFeedbackSection) {
          userFeedbackSection.style.display = "block"; // Or whatever makes it visible
          initializeUserRatingUI(); // Resets stars, feedback text
          userFeedbackSection.scrollIntoView({
            behavior: "smooth",
            block: "center",
          }); // Focus it
        }
        // Note: Your existing JS already shows the feedback textarea for low ratings
        // based on star clicks, so the backend doesn't strictly need to tell it to do that again.
        break;
      case "intensity_update":
        if (simIntensity)
          simIntensity.textContent = `${
            payload.current_intensity_mod?.toFixed(1) || "?"
          }x`;
        addMessage(
          "system-alert",
          "Intensity Shift",
          `Intensity updated. Reason: ${payload.reason || "Load change"}`
        );
        break;
      case "system_status_update":
        addMessage(
          "system",
          "Status Change",
          `System ${payload.system_key} -> ${payload.status}. ${
            payload.reason ? `Reason: ${payload.reason}` : ""
          }`
        );
        break;
      case "agent_status_update":
        {
          const agentName = payload.agent_name;
          const newState = payload.state;
          if (
            !["trying_to_call_cto", "waiting_cto_response"].includes(newState)
          ) {
          }
        }
        break;
      case "full_status_update":
        if (payload.system_status) updateSystemStatusUI(payload.system_status);
        if (payload.agent_status) updateAgentStatusUI(payload.agent_status);
        if (payload.missed_calls) updateMissedCallsUI(payload.missed_calls);
        break;
      case "missed_calls_update":
        updateMissedCallsUI(payload.missed_calls || []);
        break;
      case "call_waiting":
        {
          const waitingAgent = payload.agent_name;
          const currentCall = payload.current_call || "None";
          const callWaitingActions = [
            {
              text: "Answer",
              classes: ["btn-answer-call"],
              command: "answer call",
            },
            {
              text: "Ignore",
              classes: ["btn-ignore-call"],
              command: "ignore call",
            },
          ];
          addMessage(
            "system-alert",
            "CALL WAITING",
            `${waitingAgent} is calling. Current call: ${currentCall}.`,
            null,
            callWaitingActions
          );
        }
        break;
      case "call_ignored":
        break;
      case "display_message":
        {
          const speaker = payload.speaker || "Unknown";
          const messageText = payload.message || "";
          const notificationText = payload.notification;
          if (
            speaker === "Call Ignored" &&
            lastPlayerActionSent === "ignore call"
          ) {
            lastPlayerActionSent = null;
            break;
          }
          const playerNameDisp = playerInput?.dataset.playerName || "Player";
          let messageType = "system";
          if (speaker === playerNameDisp) {
            messageType = "player";
          } else if (
            [
              "System",
              "System Decision",
              "System Alert",
              "System Status",
              "System Command",
              "Internal Comm",
              "SIMULATION CORE",
              "Intensity Shift",
              "Call Waiting",
              "Call Ignored",
              "Conversation",
              "Backend Activity",
              "WebSocket",
              "Command Parser",
            ].includes(speaker)
          ) {
            const typeSuffix = speaker.split(" ")[1]?.toLowerCase() || "info";
            messageType = `system-${typeSuffix}`;
            if (speaker === "Command Parser") messageType = "system-warning";
            if (speaker === "Call Ignored") messageType = "system-info";
          } else {
            messageType = "agent";
          }
          addMessage(messageType, speaker, messageText, notificationText, null);
          if (
            messageType === "agent" &&
            typeof showAgentThinking === "function"
          ) {
            showAgentThinking(speaker, false);
          }
        }
        break;
      case "agent_thinking":
        showAgentThinking(payload.agent_name, true);
        break;
      case "conversation_started":
        {
          const startedAgentName = payload.agent_name;
          addMessage(
            "system",
            "Conversation",
            `Started conversation with ${startedAgentName}. Use 'hang up' or 🚫 to end.`
          );
          agentCurrentlyInConversation = startedAgentName;
          Object.keys(activeAgentCallButtons).forEach((name) => {
            const agentUI = activeAgentCallButtons[name];
            if (agentUI) {
              if (name === startedAgentName) {
                agentUI.button.classList.add("hidden");
                agentUI.endButton.classList.remove("hidden");
              } else {
                agentUI.button.classList.remove("hidden");
                agentUI.endButton.classList.add("hidden");
              }
              if (agentUI.indicator) agentUI.indicator.classList.add("hidden");
            }
          });
        }
        break;
      case "conversation_ended":
        {
          const endedAgentName = payload.agent_name;
          addMessage(
            "system",
            "Conversation",
            `Ended conversation with ${endedAgentName}.`
          );
          if (endedAgentName === agentCurrentlyInConversation) {
            const agentUI = activeAgentCallButtons[endedAgentName];
            if (agentUI) {
              agentUI.button.classList.remove("hidden");
              agentUI.endButton.classList.add("hidden");
              if (agentUI.indicator) agentUI.indicator.classList.add("hidden");
            }
            agentCurrentlyInConversation = null;
          } else {
            agentCurrentlyInConversation = null;
            Object.values(activeAgentCallButtons).forEach((ui) => {
              if (ui) {
                ui.button.classList.remove("hidden");
                ui.endButton.classList.add("hidden");
                if (ui.indicator) ui.indicator.classList.add("hidden");
              }
            });
          }
        }
        break;
      case "decision_point_info":
        showDecisionPoint(payload);
        if (payload.current_status_dict)
          updateSystemStatusUI(payload.current_status_dict);
        break;
      case "request_yes_no":
        {
          const isModalActiveReq =
            debriefModal && debriefModal.classList.contains("active");
          if (isModalActiveReq) {
            pendingYesNoPayload = payload;
          } else {
            showYesNoPrompt(payload);
          }
        }
        break;
      case "request_analyst_input":
        showAnalystBriefingInput(payload);
        break;
      case "debrief_info":
        showDebriefModal(payload);
        break;
      case "debrief_rating_update":
        {
          if (payload.performance_rating) {
            const isModalActiveRate =
              debriefModal && debriefModal.classList.contains("active");
            const isYesNoPendingRate = !!pendingYesNoPayload;
            if (isYesNoPendingRate) {
              pendingRatingUpdatePayload = payload;
            } else if (isModalActiveRate) {
              pendingRatingUpdatePayload = payload;
              if (ratingError)
                ratingError.textContent =
                  "Updated ratings available after closing.";
            } else {
              showDebriefModal(payload);
            }
          }
        }
        break;
      case "simulation_ended":
        {
          stopSimTimer();
          addMessage(
            "system-alert",
            "Simulation End",
            payload.message || "Simulation Complete."
          );
          currentSimState = "ENDED";
          setSimStatus("Ended", "ended");
          if (playerInput) playerInput.disabled = true;
          if (playerInputForm) playerInputForm.classList.add("disabled");
          hideInteractionContainers();
          const isModalShowingEnd =
            debriefModal && debriefModal.classList.contains("active");
          if (!isModalShowingEnd && payload.debrief_data) {
            showDebriefModal(payload.debrief_data);
          }
          closeWebSocket();
          validatePlayerInput();
        }
        break;
      case "error_message":
        addMessage("system-error", "Backend Error", payload.message);
        break;
      default:
    }
  }

  function handleStateChange(newState) {
    currentSimState = newState;
    const isInputAllowed = ![
      "SETUP",
      "INITIALIZING",
      "PAUSED",
      "ENDED",
      "ERROR",
      "DEBRIEFING",
      "AGENT_PROCESSING",
    ].includes(currentSimState);
    const enableInput =
      isInputAllowed && socket && socket.readyState === WebSocket.OPEN;
    if (playerInput) {
      playerInput.disabled = !enableInput;
    }
    if (playerInputForm) {
      playerInputForm.classList.toggle("disabled", !enableInput);
    }
    validatePlayerInput();
    if (
      ![
        "DECISION_POINT_SHUTDOWN",
        "AWAITING_ANALYST_BRIEFING",
        "POST_INITIAL_CRISIS",
      ].includes(currentSimState)
    ) {
    } else {
      validatePlayerInput();
    }
    setSimStatus(currentSimState.replace(/_/g, " "));
  }

  function handleSimulationUiSetup(payload) {
    if (!setupScreen || !simulationInterface) {
      return;
    }
    setupScreen.classList.remove("active");
    simulationInterface.classList.add("active");
    const scenario = payload.scenario || "Simulation";
    const playerName = payload.player_name || "Player";
    const playerRole = payload.player_role || "Role";
    simHeaderTitle.textContent = scenario;
    simPlayerInfo.textContent = `${playerName} (${playerRole})`;
    stopSimTimer();
    if (payload.start_time_iso) {
      try {
        localSimTime = new Date(payload.start_time_iso);
        if (isNaN(localSimTime.getTime())) throw new Error("Invalid Date");
        if (simTimeClock)
          simTimeClock.textContent = formatTimeLocal(payload.start_time_iso);
      } catch (e) {
        localSimTime = null;
        if (simTimeClock) simTimeClock.textContent = "??:??:??";
      }
    } else if (simTimeClock) {
      localSimTime = null;
      simTimeClock.textContent = "--:--:--";
    }
    if (payload.end_time_iso && simEndTime) {
      simEndTime.textContent = formatTimeLocal(payload.end_time_iso);
    } else if (simEndTime) {
      simEndTime.textContent = "--:--:--";
    }
    if (payload.current_intensity_mod)
      simIntensity.textContent = `${payload.current_intensity_mod.toFixed(1)}x`;
    playerInput.dataset.playerName = playerName;
    messageDisplay.innerHTML = "";
    logFeedList.innerHTML = "";
    agentCurrentlyInConversation = null;
    activeAgentCallButtons = {};
    hideInteractionContainers();
    if (payload.initial_system_status) {
      updateSystemStatusUI(payload.initial_system_status);
    }
    if (payload.initial_agent_status) {
      updateAgentStatusUI(payload.initial_agent_status);
    }
    const allSidePanels = sideColumn.querySelectorAll(".status-panel");
    allSidePanels.forEach((panel) => {
      const toggleButton = panel.querySelector(".btn-panel-toggle");
      const iconSpan = panel.querySelector(".toggle-icon");
      const headerH4 = panel.querySelector(".panel-header h4");
      panel.classList.remove("panel-minimized");
      if (toggleButton) {
        toggleButton.setAttribute("aria-expanded", "true");
      }
      if (iconSpan) {
        iconSpan.textContent = "-";
      }
      if (headerH4) {
        headerH4.style.borderBottomColor = "";
      }
    });
    if (localSimTime) {
      startSimTimer();
    }
    playerInput.focus();
    addMessage(
      "system-alert",
      "Simulation Start",
      `Welcome, ${playerRole} ${playerName}. ${scenario} simulation initialized and running.`
    );
  }

  if (
    startSimButton &&
    scenarioSelect &&
    intensitySelect &&
    durationSelect &&
    setupError
  ) {
    startSimButton.addEventListener("click", async () => {
      const scenario = scenarioSelect.value;
      const intensity = intensitySelect.value;
      const duration = durationSelect.value;
      if (!scenario || !intensity || !duration) {
        setupError.textContent = "Select scenario, intensity, duration.";
        return;
      }
      setupError.textContent = "";
      startSimButton.disabled = true;
      startSimButton.textContent = "Checking...";
      const authToken = localStorage.getItem("accessToken");
      const simConfig = { scenario, intensity, duration: parseInt(duration) };
      if (authToken) {
        startSimButton.textContent = "Initializing...";
        currentAuthToken = authToken;
        addMessage(
          "system-info",
          "System",
          "Starting authenticated simulation..."
        );
        const response = await apiCall("/sim/start", "POST", simConfig, true);
        if (response && response.simulation_id) {
          currentSimulationId = response.simulation_id;
          initializeWebSocket(currentSimulationId, currentAuthToken);
          startSimButton.textContent = "Connecting...";
          setSimStatus("Connecting WS", "paused");
        } else {
          startSimButton.disabled = false;
          startSimButton.textContent = "Initialize Pressure Chamber";
          if (setupError && !setupError.textContent) {
            setupError.textContent = "Failed to start simulation.";
          }
        }
      } else {
        currentAuthToken = null;
        const hasViewedDemo = sessionStorage.getItem(SESSION_STORAGE_DEMO_FLAG);
        if (hasViewedDemo) {
          startSimButton.textContent = "Initializing...";
          addMessage("system-info", "System", "Starting guest simulation...");
          const response = await apiCall(
            "/sim/start_guest",
            "POST",
            simConfig,
            false
          );
          if (response && response.simulation_id) {
            currentSimulationId = response.simulation_id;
            initializeWebSocket(currentSimulationId, null);
            startSimButton.textContent = "Connecting...";
            setSimStatus("Connecting WS", "paused");
          } else {
            startSimButton.disabled = false;
            startSimButton.textContent = "Initialize Pressure Chamber";
            if (setupError && !setupError.textContent) {
              setupError.textContent = "Failed to start guest simulation.";
            }
          }
        } else {
          addMessage(
            "system-info",
            "System",
            "Redirecting to simulation demo first..."
          );
          sessionStorage.setItem(SESSION_STORAGE_DEMO_FLAG, "true");
          sessionStorage.setItem(
            SESSION_STORAGE_PENDING_CONFIG,
            JSON.stringify(simConfig)
          );
          window.location.href = "/simulation-demo";
        }
      }
    });
  } else {
  }

  if (playerInputForm && playerInput) {
    playerInputForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const isValid = validatePlayerInput();
      if (!isValid) {
        return;
      }

      const action = playerInput.value.trim();
      if (!action || playerInput.disabled) {
        return;
      }

      lastPlayerActionSent = action.toLowerCase();
      const playerName = playerInput.dataset.playerName || "Player";
      addMessage("player", playerName, action);
      playerInput.value = "";
      validatePlayerInput();

      if (
        analystBriefingContainer &&
        !analystBriefingContainer.classList.contains("hidden")
      ) {
        submitBriefing(action);
      } else if (
        decisionPointContainer &&
        !decisionPointContainer.classList.contains("hidden")
      ) {
        hideInteractionContainers();
        sendPlayerAction(action);
      } else if (
        yesNoPromptContainer &&
        !yesNoPromptContainer.classList.contains("hidden")
      ) {
        hideInteractionContainers();
        sendPlayerAction(action);
      } else {
        sendPlayerAction(action);
      }
    });
  }

  if (playerInput) {
    playerInput.addEventListener("input", validatePlayerInput);
  }

  if (submitBriefingButton && analystBriefingInput) {
    submitBriefingButton.addEventListener("click", () => {
      const points = analystBriefingInput.value.trim();
      if (!points) return;
      hideInteractionContainers();
      const playerName = playerInput?.dataset.playerName || "Player";
      addMessage("player", playerName, `Briefing submitted: ${points}`);
      addMessage(
        "system",
        "System",
        "Analyst briefing points submitted for review."
      );
      analystBriefingInput.value = "";
      submitBriefing(points);
    });
  }
  async function submitBriefing(points) {
    if (!currentSimulationId) {
      addMessage(
        "system-error",
        "System",
        "Error submitting briefing: No active simulation ID."
      );
      return;
    }
    const endpoint = `/sim/${currentSimulationId}/briefing`;
    const payload = { talking_points: points };
    const response = await apiCall(
      endpoint,
      "POST",
      payload,
      !!currentAuthToken
    );
    if (!response) {
      addMessage(
        "system-error",
        "System",
        "Error submitting briefing points. Check connection."
      );
    }
  }

  if (closeDebriefButton) {
    closeDebriefButton.addEventListener("click", hideDebriefModal);
  }
  if (debriefModal) {
    debriefModal.addEventListener("click", (e) => {
      if (e.target === debriefModal) hideDebriefModal();
    });
  }

  const panelToggleButtons = document.querySelectorAll(".btn-panel-toggle");
  panelToggleButtons.forEach((button) => {
    if (button.dataset.listenerAttached) return;
    button.addEventListener("click", () => {
      const panel = button.closest(".status-panel");
      const iconSpan = button.querySelector(".toggle-icon");
      if (!panel || !iconSpan) return;
      panel.classList.toggle("panel-minimized");
      const isMinimized = panel.classList.contains("panel-minimized");
      iconSpan.textContent = isMinimized ? "+" : "-";
      button.setAttribute("aria-expanded", String(!isMinimized));
      const headerH4 = panel.querySelector(".panel-header h4");
      if (headerH4) {
        headerH4.style.borderBottomColor = isMinimized ? "transparent" : "";
      }
    });
    button.dataset.listenerAttached = "true";
  });

  function handlePanelFocusClick(event) {
    const focusButton = event.target.closest(".btn-panel-focus");
    if (focusButton) {
      focusPanel(this);
    }
  }
  if (systemStatusPanel) {
    systemStatusPanel.addEventListener("click", handlePanelFocusClick);
  }
  if (agentStatusPanel) {
    agentStatusPanel.addEventListener("click", handlePanelFocusClick);
  }
  if (logFeedPanel) {
    logFeedPanel.addEventListener("click", handlePanelFocusClick);
  }
  if (defocusPanelBtn) {
    defocusPanelBtn.addEventListener("click", defocusPanel);
  }

  if (commandHelperBtn && commandDropdown) {
    commandHelperBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const isHidden = commandDropdown.classList.toggle("hidden");
      commandHelperBtn.setAttribute("aria-expanded", String(!isHidden));
    });
  }
  if (commandDropdown && playerInput) {
    commandDropdown.addEventListener("click", (event) => {
      if (event.target.classList.contains("command-item")) {
        const command = event.target.dataset.command;
        if (command) {
          const commandText =
            command === "isolate" || command === "block ip"
              ? command + " "
              : command;
          playerInput.value = commandText;
          playerInput.focus();
          validatePlayerInput();
          commandDropdown.classList.add("hidden");
          if (commandHelperBtn)
            commandHelperBtn.setAttribute("aria-expanded", "false");
        }
      }
    });
  }
  document.addEventListener("click", (event) => {
    if (commandDropdown && !commandDropdown.classList.contains("hidden")) {
      if (
        !commandDropdown.contains(event.target) &&
        !(commandHelperBtn && commandHelperBtn.contains(event.target))
      ) {
        commandDropdown.classList.add("hidden");
        if (commandHelperBtn)
          commandHelperBtn.setAttribute("aria-expanded", "false");
      }
    }
  });
  if (showOrgChartBtn) {
    showOrgChartBtn.addEventListener("click", openMainOrgChartModal);
  } else {
    Logger.warn("Header org chart button (#show-org-chart-btn) not found.");
  }

  if (closeIframeModalButton) {
    closeIframeModalButton.addEventListener("click", closeMainOrgChartModal);
  }
  if (iframeModal) {
    iframeModal.addEventListener("click", (event) => {
      if (event.target === iframeModal) {
        closeMainOrgChartModal();
      }
    });
  }
  if (exitSimBtn) {
    exitSimBtn.addEventListener("click", handleExitSimulation);
  } else {
    Logger.warn("Header exit button (#exit-sim-btn) not found.");
  }
  window.addEventListener("beforeunload", handleBeforeUnload);
  window.addEventListener("resize", handleResize);

  const didStartPending = checkAndStartPendingSimulation();

  if (!didStartPending) {
    Logger.info("Initial Load: No pending simulation found, showing setup.");

    if (focusModeControls) focusModeControls.classList.add("hidden");
    if (playerInput) playerInput.disabled = true;
    if (playerInputForm) playerInputForm.classList.add("disabled");
    setSimStatus("Setup");
    agentCurrentlyInConversation = null;
    if (setupScreen) setupScreen.classList.add("active");
    if (simulationInterface) simulationInterface.classList.remove("active");
    validatePlayerInput();
    clearSimulationUI();
  } else {
    Logger.info(
      "Initial Load: Pending simulation detected, attempting to resume."
    );
  }

  manageSwipeListeners();

  if (currentlyFocusedPanel) {
    defocusPanel();
  }
  document.body.classList.remove("panel-is-focused");
  if (focusModeControls) focusModeControls.classList.add("hidden");
});
