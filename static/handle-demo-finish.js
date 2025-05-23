// static/handle-demo-finish.js - Refactored to use Logger

// Ensure Logger is available (it should be if utils.js loads first)
if (typeof Logger === "undefined") {
  console.error(
    "Logger utility not found! Cannot initialize handle-demo-finish.js logging."
  );
  // Fallback to console if Logger is missing
  window.Logger = {
    debug: console.debug,
    info: console.info,
    warn: console.warn,
    error: console.error,
  };
}

Logger.info("Demo page finish handler script loaded.");

document.addEventListener("DOMContentLoaded", () => {
  // Target buttons with the specific class '.js-finish-demo-trigger'
  // This includes the "Skip Demo" button in the prompt and the "Close Demo" button
  const finishTriggerButtons = document.querySelectorAll(
    ".js-finish-demo-trigger"
  );
  const statusMessage = document.getElementById("demo-status-message"); // Optional status display

  // Use the same session storage keys as your main application logic would expect
  const SESSION_STORAGE_PENDING_CONFIG = "pendingGuestSimConfig";
  const SESSION_STORAGE_ACTIVE_SIM = "activeSimulationId";

  if (finishTriggerButtons.length > 0) {
    Logger.debug(
      `Found ${finishTriggerButtons.length} finish trigger buttons.`
    );

    finishTriggerButtons.forEach((button) => {
      button.addEventListener("click", async (event) => {
        Logger.info("Finish/Skip Demo button clicked.", {
          buttonId: event.target.id,
          buttonText: event.target.textContent,
        });

        if (statusMessage)
          statusMessage.textContent = "Checking configuration...";
        button.disabled = true;
        // Change text content based on which button it might be
        button.textContent =
          button.textContent.includes("Skip") ||
          button.textContent.includes("Close")
            ? "Loading..."
            : "Starting...";

        const storedConfigString = sessionStorage.getItem(
          SESSION_STORAGE_PENDING_CONFIG
        );

        if (!storedConfigString) {
          Logger.error(
            "Could not find pending simulation config in sessionStorage.",
            { key: SESSION_STORAGE_PENDING_CONFIG }
          );
          if (statusMessage)
            statusMessage.textContent =
              "Error: Could not retrieve your simulation settings. Please configure again.";
          // Optional: Redirect back to configuration page if applicable
          // window.location.href = '/simulation'; // Example redirect
          button.disabled = false; // Re-enable button on error
          button.textContent = button.textContent.includes("Loading")
            ? button.id === "close-demo-button"
              ? "Close Demo"
              : "Skip Demo"
            : "Start Simulation"; // Restore original-like text
          return;
        }

        try {
          const simConfig = JSON.parse(storedConfigString);
          Logger.debug(
            "Attempting to start simulation with config:",
            simConfig
          );
          if (statusMessage)
            statusMessage.textContent = "Initializing your simulation...";

          // Ensure apiCall is defined (should be from utils.js)
          if (typeof apiCall !== "function") {
            Logger.error(
              "apiCall function is not defined. Cannot start simulation."
            );
            throw new Error("apiCall function is missing.");
          }

          // Call the guest start endpoint
          const response = await apiCall(
            "/sim/start_guest",
            "POST",
            simConfig,
            false
          );

          if (response && response.simulation_id) {
            Logger.info(
              "Guest simulation started successfully via demo page.",
              { simId: response.simulation_id }
            );
            if (statusMessage)
              statusMessage.textContent = "Simulation ready! Redirecting...";

            // Store the *new* active simulation ID
            sessionStorage.setItem(
              SESSION_STORAGE_ACTIVE_SIM,
              response.simulation_id
            );
            Logger.debug("Stored active simulation ID in sessionStorage.", {
              key: SESSION_STORAGE_ACTIVE_SIM,
              value: response.simulation_id,
            });

            // Clean up the pending config
            sessionStorage.removeItem(SESSION_STORAGE_PENDING_CONFIG);
            Logger.debug("Removed pending config from sessionStorage.", {
              key: SESSION_STORAGE_PENDING_CONFIG,
            });

            // Redirect back to the main simulation page
            Logger.info("Redirecting to /simulation page.");
            window.location.href = "/simulation"; // Adjust if your main page URL is different
          } else {
            Logger.error("Failed to start guest simulation from demo page.", {
              response: response,
            });
            if (statusMessage)
              statusMessage.textContent = `Error starting simulation: ${
                response?.detail || "Unknown error"
              }. Please try again.`;
            button.disabled = false; // Re-enable button on error
            button.textContent = button.textContent.includes("Loading")
              ? button.id === "close-demo-button"
                ? "Close Demo"
                : "Skip Demo"
              : "Start Simulation";
          }
        } catch (error) {
          Logger.error("Error processing finish/skip demo action:", {
            error: error,
          });
          if (statusMessage)
            statusMessage.textContent =
              "An unexpected error occurred. Please check console logs and try again.";
          button.disabled = false; // Re-enable button on error
          button.textContent = button.textContent.includes("Loading")
            ? button.id === "close-demo-button"
              ? "Close Demo"
              : "Skip Demo"
            : "Start Simulation";
        }
      });
    });
    Logger.debug("Finish demo listeners attached to all trigger buttons.");
  } else {
    Logger.warn(
      "No finish trigger buttons found with class '.js-finish-demo-trigger'."
    );
  }
});

document.addEventListener("DOMContentLoaded", () => {
  console.log("Demo page finish handler script loaded.");

  // --- MODIFICATION: Select all buttons that trigger the finish action ---
  const finishTriggers = document.querySelectorAll(".js-finish-demo-trigger");
  // --- End Modification ---

  const statusMessage = document.getElementById("demo-status-message");
  const SESSION_STORAGE_PENDING_CONFIG = "pendingGuestSimConfig";
  const SESSION_STORAGE_ACTIVE_SIM = "activeSimulationId";

  // --- MODIFICATION: Check if any trigger buttons were found ---
  if (!finishTriggers || finishTriggers.length === 0) {
    console.error(
      "Error: No finish trigger buttons (.js-finish-demo-trigger) found on demo page."
    );
    // Optional: Display an error in the status message if it exists
    if (statusMessage)
      statusMessage.textContent = "Error: UI elements missing.";
    return;
  } else {
    console.log(`Found ${finishTriggers.length} finish trigger buttons.`);
  }
  // --- End Modification ---

  // Status message is optional
  if (!statusMessage) {
    console.warn(
      "Warning: Status message element (#demo-status-message) not found on demo page."
    );
  }

  // --- MODIFICATION: Loop and attach listener to each button ---
  finishTriggers.forEach((button) => {
    button.addEventListener("click", async () => {
      // Log which button was clicked
      console.log(`Finish Demo triggered by: "${button.textContent.trim()}"`);

      if (statusMessage)
        statusMessage.textContent = "Retrieving your configuration...";

      // Disable the SPECIFIC button that was clicked
      button.disabled = true;
      const originalButtonText = button.textContent; // Store original text for potential re-enable
      button.textContent = "Starting...";

      const storedConfigString = sessionStorage.getItem(
        SESSION_STORAGE_PENDING_CONFIG
      );

      if (!storedConfigString) {
        console.error(
          "Could not find pending simulation config in sessionStorage."
        );
        if (statusMessage)
          statusMessage.textContent =
            "Error: Could not find your simulation settings. Please return to setup.";
        // Re-enable the clicked button
        button.disabled = false;
        button.textContent = originalButtonText;
        return;
      }

      try {
        const simConfig = JSON.parse(storedConfigString);
        console.log("Attempting to start simulation with config:", simConfig);
        if (statusMessage)
          statusMessage.textContent = "Initializing your simulation...";

        // Ensure apiCall is defined before calling it
        if (typeof apiCall !== "function") {
          throw new Error(
            "apiCall function is not defined. Ensure utils.js is loaded correctly before this script."
          );
        }
        // console.log("Inside click listener, typeof apiCall:", typeof apiCall); // Keep for debugging if needed

        const response = await apiCall(
          "/api/sim/start_guest",
          "POST",
          simConfig,
          false // Assuming guest calls don't need auth header
        );

        if (response && response.simulation_id) {
          console.log(
            "Guest simulation started successfully via API, ID:",
            response.simulation_id
          );
          if (statusMessage)
            statusMessage.textContent = "Simulation ready! Redirecting...";

          sessionStorage.setItem(
            SESSION_STORAGE_ACTIVE_SIM,
            response.simulation_id
          );
          sessionStorage.removeItem(SESSION_STORAGE_PENDING_CONFIG); // Clean up pending config

          // Add a small delay before redirecting to allow user to read message
          await new Promise((resolve) => setTimeout(resolve, 500));

          window.location.href = "/simulation"; // Redirect to the main simulation page
        } else {
          console.error(
            "API call failed to start guest simulation from demo page.",
            response
          );
          if (statusMessage)
            statusMessage.textContent = `Error starting simulation: ${
              response?.detail || "Unknown API error. Check console."
            }`;
          // Re-enable the clicked button
          button.disabled = false;
          button.textContent = originalButtonText;
        }
      } catch (error) {
        console.error("Error processing finish demo click:", error);
        if (statusMessage) {
          if (error instanceof SyntaxError) {
            statusMessage.textContent =
              "Error: Invalid simulation settings format.";
          } else {
            statusMessage.textContent = `An error occurred: ${
              error.message || "Please try again."
            }`;
          }
        }
        // Re-enable the clicked button
        button.disabled = false;
        button.textContent = originalButtonText;
      }
    }); // End addEventListener for this button
  }); // End forEach loop
  // --- End Modification ---

  console.log("Finish demo listeners attached to all trigger buttons.");
}); // End DOMContentLoaded
