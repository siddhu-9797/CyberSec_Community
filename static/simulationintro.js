document.addEventListener("DOMContentLoaded", () => {
  const MOBILE_BREAKPOINT = 768;

  const scenarioSelect = document.getElementById("scenario-select");
  const intensitySelect = document.getElementById("intensity-select");
  const durationSelect = document.getElementById("duration-select");
  const startButton = document.getElementById("start-sim-button");
  const setupScreen = document.getElementById("setup-screen");
  const explanationArea = document.getElementById("scenario-explanation-area");

  const iframeModal = document.getElementById("iframe-modal");
  const iframeModalBody = document.getElementById("iframe-modal-body");
  const closeIframeModalButton = document.getElementById("close-iframe-modal");

  if (
    !scenarioSelect ||
    !intensitySelect ||
    !durationSelect ||
    !startButton ||
    !setupScreen ||
    !explanationArea
  ) {
  } else {
    scenarioSelect.addEventListener("change", () => {
      updateSetupControlsForDemo();
      updateScenarioExplanation();
    });

    updateSetupControlsForDemo();
    updateScenarioExplanation();
  }

  if (!iframeModal || !iframeModalBody || !closeIframeModalButton) {
  } else {
    closeIframeModalButton.addEventListener("click", closeOrgChartModal);
    iframeModal.addEventListener("click", (event) => {
      if (event.target === iframeModal) {
        closeOrgChartModal();
      }
    });
  }

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (
        scenarioSelect &&
        explanationArea &&
        !explanationArea.classList.contains("hidden")
      ) {
        updateScenarioExplanation();
      }
    }, 250);
  });

  function updateSetupControlsForDemo() {
    if (!scenarioSelect || !intensitySelect || !durationSelect) return;
    const isDemo = scenarioSelect.value === "DemoSimulation";
    intensitySelect.disabled = isDemo;
    durationSelect.disabled = isDemo;
    if (isDemo) {
      intensitySelect.value = "Medium";
      durationSelect.value = 2;
    }
  }

  function updateScenarioExplanation() {
    if (!scenarioSelect || !explanationArea) return;
    const selectedValue = scenarioSelect.value;

    if (
      selectedValue &&
      selectedValue !== "DemoSimulation" &&
      selectedValue !== ""
    ) {
      //   const orgChartUrl = "https://profile.haktopus.com";
      const orgChartUrl = "http://localhost:3000/";
      const isMobileView = window.innerWidth < MOBILE_BREAKPOINT;
      let chartHTML = "";

      if (isMobileView) {
        chartHTML = `
              <p style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
                  <button id="view-org-chart-btn" class="btn btn-secondary" data-url="${orgChartUrl}">
                      View Security Org Chart
                  </button>
              </p>
            `;
      } else {
        chartHTML = `
              <iframe
                  src="${orgChartUrl}"
                  width="100%"
                  height="450px" /* Keep original desktop height */
                  frameborder="0"
                  style="border:none; display: block; margin: 20px auto;" /* Center iframe slightly */
                  title="CPM Security Org Chart">
              </iframe>
            `;
      }

      const explanationHTML = `
          <h4>Scenario Briefing: Your Role as CISO</h4>
          <p>
          Imagine this: You're the <strong>Chief Information Secuirty Officer (CISO)</strong> of a major global currency exchange. You're currently on a vital business trip in London, wrapping up negotiations. Suddenly, an encrypted emergency communication flashes on your device – it's <strong>midnight</strong> back at headquarters.
          </p>
          <p>
          The message is stark and urgent. Critical systems are failing. <strong>'ICE'</strong> – the Integrated Core Exchange platform – is experiencing catastrophic anomalies. Trading systems are unresponsive, client portals are crashing, and internal communications are becoming unreliable. Your technical teams are scrambling, but the root cause is unclear.
          </p>
          <p>
          This isn't just a technical glitch; it's a full-blown crisis. <strong>Your decisions</strong> in the immediate future are paramount. How you direct your team, manage resources, and communicate internally will directly impact the company's operational stability, reputation, and potentially its standing in the financial markets.
          </p>
          ${chartHTML}
          <p>
          Amidst the chaos, you also need to think about external perception. Prepare some initial, <strong>concise briefing points</strong> for the communications team. The goal is reassurance and control – formulate statements that won't trigger panic or negatively impact company stocks while the situation is assessed. <strong>Every word matters.</strong>
          </p>
          <p>
          The clock is ticking. Verify the simulation parameters below and prepare to enter the pressure chamber.
          </p>
        `;

      explanationArea.innerHTML = explanationHTML;
      explanationArea.classList.remove("hidden");

      if (isMobileView) {
        const viewChartBtn = document.getElementById("view-org-chart-btn");
        if (viewChartBtn) {
          viewChartBtn.removeEventListener("click", openOrgChartModal);
          viewChartBtn.addEventListener("click", openOrgChartModal);
        } else {
        }
      }
    } else {
      explanationArea.classList.add("hidden");
      explanationArea.innerHTML = "";
    }
  }

  function openOrgChartModal(event) {
    if (!iframeModal || !iframeModalBody) {
      return;
    }
    const url = event.currentTarget.dataset.url;
    if (!url) {
      return;
    }

    iframeModalBody.innerHTML = `
            <iframe
               src="${url}"
               frameborder="0"
               title="CPM Security Org Chart"
               style="width: 100%; height: 100%; border: none;">
            </iframe>`;
    iframeModal.classList.add("active");
    if (closeIframeModalButton) closeIframeModalButton.focus();
  }

  function closeOrgChartModal() {
    if (!iframeModal || !iframeModalBody) return;

    iframeModal.classList.remove("active");
    iframeModalBody.innerHTML = "<p>Loading chart...</p>";
  }
});
