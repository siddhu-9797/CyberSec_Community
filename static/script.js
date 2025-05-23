// script.js

document.addEventListener("DOMContentLoaded", () => {
  // Ensure GSAP plugins are registered
  if (typeof gsap !== "undefined") {
    gsap.registerPlugin(ScrollTrigger, TextPlugin);
  } else {
    console.error("GSAP library not loaded.");
    return; // Stop execution if GSAP is missing
  }

  const body = document.body;
  const preloader = document.getElementById("preloader");
  const siteHeader = document.getElementById("site-header");
  const heroTitle = document.getElementById("heroTitle");
  const mobileNavToggle = document.getElementById("mobile-nav-toggle");
  const mainNav = document.getElementById("main-nav");
  const logFeedElement = document.getElementById("logFeed");
  const simTimeElement = document.getElementById("simTime");
  const alertCountElement = document.getElementById("alertCount");
  const alertLevelElement = document.getElementById("alertLevel");
  const networkStatusElement = document.getElementById("networkStatus");
  const stressLevelElement = document.getElementById("stressLevel");
  const decisionPointsElement = document.getElementById("decisionPoints");
  // --- START: Mobile Warning Logic ---
  const mobileWarningBanner = document.getElementById("mobileWarning");
  const mobileWarningCloseBtn = mobileWarningBanner?.querySelector(
    ".mobile-warning-close"
  );
  const mobileBreakPoint = 768; // The max-width threshold (inclusive)

  let simTimerInterval;
  let logInterval;
  let currentSimTime = 0;
  let currentAlertCount = 0;
  let currentDecisionPoints = 0;
  const totalDecisionPoints = 5; // Example total

  // --- Preloader ---
  function hidePreloader() {
    if (preloader) {
      gsap.to(preloader, {
        opacity: 0,
        duration: 0.5,
        ease: "power1.out",
        onComplete: () => (preloader.style.display = "none"),
      });
    }
    body.classList.add("loaded");
    startHeroAnimations();
    initScrollAnimations();
    initCounters();
    startDashboardSimulation(); // Start dashboard simulation after load
  }

  let dependenciesLoaded =
    typeof THREE !== "undefined" && typeof Swiper !== "undefined"; // Add more checks if needed
  let minTimePassed = false;
  setTimeout(() => {
    minTimePassed = true;
    if (windowLoaded && dependenciesLoaded) hidePreloader();
  }, 1200);

  let windowLoaded = false;
  window.addEventListener("load", () => {
    windowLoaded = true;
    dependenciesLoaded =
      typeof THREE !== "undefined" && typeof Swiper !== "undefined"; // Recheck on load
    if (minTimePassed && dependenciesLoaded) hidePreloader();
    else if (!dependenciesLoaded) {
      console.warn("Dependencies (Three.js/Swiper) not loaded on window.load");
      // Optionally hide preloader anyway after a longer timeout
      setTimeout(hidePreloader, 2000);
    }
  });

  // Failsafe
  setTimeout(() => {
    if (!body.classList.contains("loaded")) {
      console.warn("Preloader timeout.");
      hidePreloader();
    }
  }, 6000);

  // --- Header Scroll Behavior ---
  ScrollTrigger.create({
    start: "top -90", // Trigger slightly later
    end: 99999,
    toggleClass: { className: "scrolled", targets: siteHeader },
  });

  // --- Mobile Navigation ---
  if (mobileNavToggle && mainNav) {
    mobileNavToggle.addEventListener("click", () => {
      const isActive = mainNav.classList.toggle("active");
      mobileNavToggle.classList.toggle("active");
      mobileNavToggle.setAttribute("aria-expanded", isActive);
      body.classList.toggle("no-scroll", isActive);
    });

    // Close nav when a link is clicked
    mainNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        mainNav.classList.remove("active");
        mobileNavToggle.classList.remove("active");
        mobileNavToggle.setAttribute("aria-expanded", "false");
        body.classList.remove("no-scroll");
      });
    });
    // Close nav on escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && mainNav.classList.contains("active")) {
        mainNav.classList.remove("active");
        mobileNavToggle.classList.remove("active");
        mobileNavToggle.setAttribute("aria-expanded", "false");
        body.classList.remove("no-scroll");
      }
    });
  }

  // --- Hero Animations ---
  function startHeroAnimations() {
    if (heroTitle) {
      gsap.to(heroTitle, {
        duration: 0.1,
        opacity: 1,
        onComplete: () => {
          let originalText = heroTitle.textContent;
          heroTitle.textContent = ""; // Clear text for typing effect
          gsap.to(heroTitle, {
            duration: 2.0, // Slightly faster typing
            text: { value: originalText, delimiter: "" },
            ease: "none",
            delay: 0.2, // Short delay before typing starts
            onComplete: () => {
              document.querySelector(".hero")?.classList.add("loaded");
              if (typeof initThreeJS === "function") initThreeJS();
            },
          });
        },
      });
    } else {
      document.querySelector(".hero")?.classList.add("loaded");
      if (typeof initThreeJS === "function") initThreeJS();
    }
  }

  // --- THREE.JS Background ---
  function initThreeJS() {
    const container = document.getElementById("heroBackground");
    if (!container || typeof THREE === "undefined") return;

    let scene, camera, renderer, points;
    let mouse = new THREE.Vector2();

    function init() {
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(
        75,
        container.offsetWidth / container.offsetHeight,
        0.1,
        1000
      );
      camera.position.z = 12; // Adjust distance

      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(container.offsetWidth, container.offsetHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5)); // Limit pixel ratio
      container.appendChild(renderer.domElement);

      // Geometry - More points, maybe different shape
      const geometry = new THREE.BufferGeometry();
      const count = 4000;
      const positions = new Float32Array(count * 3);
      const colors = new Float32Array(count * 3);
      const sizes = new Float32Array(count);

      const colorCyan = new THREE.Color(0x09eef5);
      const colorGreen = new THREE.Color(0x03fc84);
      const colorMagenta = new THREE.Color(0xfa2cff);
      const baseColor = new THREE.Color(0x6b7f99); // Tertiary text color for base

      const radius = 15;

      for (let i = 0; i < count; i++) {
        const i3 = i * 3;
        // Spherical distribution
        const phi = Math.acos(-1 + (2 * i) / count);
        const theta = Math.sqrt(count * Math.PI) * phi;

        positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
        positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        positions[i3 + 2] = radius * Math.cos(phi);

        // Color based on distance or random with weighting
        const dist =
          Math.sqrt(
            positions[i3] ** 2 + positions[i3 + 1] ** 2 + positions[i3 + 2] ** 2
          ) / radius;
        let chosenColor = baseColor;
        const rand = Math.random();
        if (rand < 0.05) chosenColor = colorCyan;
        else if (rand < 0.1) chosenColor = colorGreen;
        else if (rand < 0.15) chosenColor = colorMagenta;

        const finalColor = baseColor
          .clone()
          .lerp(chosenColor, Math.random() * 0.5 + 0.1); // Lerp for variation

        colors[i3] = finalColor.r;
        colors[i3 + 1] = finalColor.g;
        colors[i3 + 2] = finalColor.b;

        sizes[i] = Math.random() * 1.5 + 0.5; // Adjust particle size range via shader
      }

      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(positions, 3)
      );
      geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
      geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));

      const material = new THREE.ShaderMaterial({
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexColors: true,
        uniforms: {
          pointTexture: {
            value: new THREE.TextureLoader().load(
              "https://placehold.co/64x64/ffffff/000000/png?text="
            ),
          }, // Simple dot texture
          uPixelRatio: { value: Math.min(window.devicePixelRatio, 1.5) },
          uSize: { value: 25.0 }, // Base size multiplier
        },
        vertexShader: `
                    uniform float uPixelRatio;
                    uniform float uSize;
                    attribute float size;
                    attribute vec3 color;
                    varying vec3 vColor;
                    void main() {
                        vColor = color;
                        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                        gl_PointSize = size * (uSize / -mvPosition.z) * uPixelRatio;
                        gl_Position = projectionMatrix * mvPosition;
                    }
                 `,
        fragmentShader: `
                     uniform sampler2D pointTexture;
                     varying vec3 vColor;
                     void main() {
                         float strength = distance(gl_PointCoord, vec2(0.5));
                         strength = 1.0 - strength;
                         strength = pow(strength, 3.0);

                         vec3 color = mix(vec3(0.0), vColor, strength);

                         gl_FragColor = vec4(color, strength * 0.8); // Use alpha from strength
                        // gl_FragColor = vec4(vColor, 1.0) * texture2D(pointTexture, gl_PointCoord); // Texture version
                     }
                 `,
      });

      points = new THREE.Points(geometry, material);
      scene.add(points);

      window.addEventListener("mousemove", onMouseMove, false);
      window.addEventListener("resize", onWindowResize, false);
    }

    function onMouseMove(event) {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }

    function onWindowResize() {
      camera.aspect = container.offsetWidth / container.offsetHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.offsetWidth, container.offsetHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      points.material.uniforms.uPixelRatio.value = Math.min(
        window.devicePixelRatio,
        1.5
      );
    }

    const clock = new THREE.Clock();
    function animate() {
      requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      points.rotation.y = elapsedTime * 0.05;
      points.rotation.x = elapsedTime * 0.02;

      // Smooth camera movement towards mouse position
      camera.position.x += (mouse.x * 1.5 - camera.position.x) * 0.03; // Slightly more parallax
      camera.position.y += (-mouse.y * 1.5 - camera.position.y) * 0.03;
      camera.lookAt(0, 0, 0); // Look at center

      renderer.render(scene, camera);
    }

    init();
    animate();
  }

  // --- Scroll Animations ---
  function initScrollAnimations() {
    gsap.utils
      .toArray(
        ".reveal-fade, .reveal-left, .reveal-right, .reveal-up, .reveal-card"
      )
      .forEach((elem) => {
        let startPos = "top 85%";
        let delay =
          parseFloat(elem.style.getPropertyValue("--reveal-delay")) || 0; // Get delay from inline style

        // Adjust trigger point for specific sections if needed
        if (
          elem.closest(".hero-subtitle") ||
          elem.closest(".hero-cta-container")
        ) {
          // Hero elements might not need scroll trigger if handled by load/typing animation
          return; // Skip scroll trigger for hero elements animated differently
        }
        if (elem.closest(".feature-item")) {
          startPos = "top 75%"; // Trigger features a bit earlier
        }

        gsap.fromTo(
          elem,
          {
            opacity: 0,
            x: elem.classList.contains("reveal-left")
              ? -50
              : elem.classList.contains("reveal-right")
              ? 50
              : 0,
            y:
              elem.classList.contains("reveal-up") ||
              elem.classList.contains("reveal-card")
                ? 50
                : 0,
            rotateX: elem.classList.contains("reveal-card") ? -15 : 0,
            scale: elem.classList.contains("reveal-card") ? 0.95 : 1,
          },
          {
            opacity: 1,
            x: 0,
            y: 0,
            rotateX: 0,
            scale: 1,
            duration: 1.0, // Slightly longer duration
            delay: delay,
            ease: "power3.out",
            scrollTrigger: {
              trigger: elem,
              start: startPos,
              once: true,
              // markers: true, // Debugging
            },
          }
        );
      });
  }

  // --- Counter Animation ---
  function initCounters() {
    gsap.utils.toArray(".counter").forEach((counter) => {
      const target = parseFloat(counter.dataset.target);
      const format = counter.dataset.format || "int"; // int, float:N
      const duration = 2.5; // Longer duration

      const config = {
        duration: duration,
        ease: "power2.out",
        scrollTrigger: {
          trigger: counter,
          start: "top 90%",
          once: true,
        },
      };

      if (format === "int") {
        config.innerText = target;
        config.roundProps = "innerText";
      } else if (format.startsWith("float:")) {
        const decimalPlaces = parseInt(format.split(":")[1]) || 1;
        config.innerText = target;
        // Use onUpdate for precise float formatting
        let proxy = { val: 0 };
        config.onUpdate = () => {
          counter.innerText = parseFloat(proxy.val).toFixed(decimalPlaces);
        };
        // Animate the proxy object
        gsap.to(proxy, { ...config, val: target });
        // Prevent GSAP from animating innerText directly for floats
        delete config.innerText;
      } else {
        // Default to integer if format is wrong
        config.innerText = target;
        config.roundProps = "innerText";
      }

      // Check if animating innerText or proxy
      if (config.innerText !== undefined) {
        gsap.to(counter, config);
      } // else the proxy animation handles it
    });
  }

  // --- Scenario Tabs ---
  const scenarioTabsContainer = document.getElementById("scenarioTabs");
  const scenarioDetailsContainer = document.getElementById(
    "scenarioDetailsContainer"
  );
  if (scenarioTabsContainer && scenarioDetailsContainer) {
    scenarioTabsContainer.addEventListener("click", (e) => {
      if (
        e.target.classList.contains("scenario-tab") &&
        !e.target.classList.contains("active")
      ) {
        const targetScenario = e.target.dataset.scenario;

        // Update tabs
        scenarioTabsContainer
          .querySelector(".active")
          .classList.remove("active");
        e.target.classList.add("active");

        // Update details - Use GSAP for fade transition
        const activeDetail = scenarioDetailsContainer.querySelector(
          ".scenario-detail.active"
        );
        const nextDetail = scenarioDetailsContainer.querySelector(
          `#scenario-${targetScenario}`
        );

        if (activeDetail) {
          gsap.to(activeDetail, {
            opacity: 0,
            duration: 0.2,
            onComplete: () => {
              activeDetail.classList.remove("active");
              if (nextDetail) {
                nextDetail.classList.add("active");
                gsap.to(nextDetail, { opacity: 1, duration: 0.3, delay: 0.1 });
              }
            },
          });
        } else if (nextDetail) {
          // Handle case where no detail was initially active
          nextDetail.classList.add("active");
          gsap.to(nextDetail, { opacity: 1, duration: 0.3 });
        }
      }
    });
  }

  // --- Live Feed Dashboard Simulation ---
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  }

  function updateDashboardStatus() {
    if (!networkStatusElement || !alertLevelElement || !stressLevelElement)
      return;

    // Simulate Network Status Change
    const netRand = Math.random();
    if (netRand < 0.1) {
      networkStatusElement.textContent = "High";
      networkStatusElement.className = "stat-value traffic-high";
    } else if (netRand < 0.3) {
      networkStatusElement.textContent = "Medium";
      networkStatusElement.className = "stat-value traffic-medium";
    } else {
      networkStatusElement.textContent = "Normal";
      networkStatusElement.className = "stat-value traffic-normal";
    }

    // Simulate Alert Level Change
    const alertRand = Math.random();
    if (alertRand < 0.15) {
      currentAlertCount += Math.floor(Math.random() * 3) + 1;
      alertLevelElement.textContent = "High";
      alertLevelElement.className = "stat-value alert-high";
    } else if (alertRand < 0.4) {
      currentAlertCount += Math.floor(Math.random() * 2);
      alertLevelElement.textContent = "Medium";
      alertLevelElement.className = "stat-value alert-medium";
    } else {
      alertLevelElement.textContent = "Low";
      alertLevelElement.className = "stat-value alert-low";
    }
    if (alertCountElement) alertCountElement.textContent = currentAlertCount;

    // Simulate Stress Level Change (could be tied to alerts/time)
    const stressRand = Math.random();
    if (currentAlertCount > 5 || currentSimTime > 300) {
      // Example condition
      stressLevelElement.textContent = "High";
      stressLevelElement.className = "stat-value stress-high";
    } else if (currentAlertCount > 2 || currentSimTime > 120) {
      stressLevelElement.textContent = "Medium";
      stressLevelElement.className = "stat-value stress-medium";
    } else {
      stressLevelElement.textContent = "Calm";
      stressLevelElement.className = "stat-value stress-low";
    }

    // Simulate Decision Points
    if (Math.random() < 0.05 && currentDecisionPoints < totalDecisionPoints) {
      // Low chance each tick
      currentDecisionPoints++;
      if (decisionPointsElement)
        decisionPointsElement.textContent = `${currentDecisionPoints} / ${totalDecisionPoints}`;
    }
  }

  function checkScreenSize() {
    // Check if warning was dismissed during this session
    if (sessionStorage.getItem("mobileWarningDismissed") === "true") {
      mobileWarningBanner.style.display = "none";
      return;
    }

    // Show warning if screen width is at or below the breakpoint
    if (window.innerWidth <= mobileBreakPoint) {
      mobileWarningBanner.style.display = "flex"; // Use 'flex' as defined in CSS
    } else {
      mobileWarningBanner.style.display = "none";
    }
  }

  if (mobileWarningBanner && mobileWarningCloseBtn) {
    // Initial check on page load
    checkScreenSize();

    // Check screen size on resize (with debounce to avoid performance issues)
    let resizeTimer;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(checkScreenSize, 250); // Check 250ms after resize stops
    });

    // Add event listener for the close button
    mobileWarningCloseBtn.addEventListener("click", () => {
      mobileWarningBanner.style.display = "none";
      // Remember that the user closed the warning for this session
      sessionStorage.setItem("mobileWarningDismissed", "true");
    });
  }
  // --- END: Mobile Warning Logic ---

  function addSimulatedLogEntry() {
    if (!logFeedElement) return;

    const li = document.createElement("li");
    const timestamp = `[${formatTime(currentSimTime)}]`;
    const logTypes = ["info", "user", "alert", "warning", "system"];
    const sources = [
      "AuthSvc",
      "NetMon",
      "Firewall",
      "Endpoint",
      "Dr. Thorne",
      "Jax",
      "Cmdr. Valerius",
      "Anya Sharma",
      "SimEngine",
    ];
    const messages = [
      "Anomalous login detected from geo-unlikely region.",
      "Significant traffic spike observed on port 443.",
      "Outbound connection to known C2 server blocked.",
      "Malware signature EKL- Ransom.Win32 detected.",
      "Investigating IoC hash: a1b2c3d4...",
      "Attempting network segmentation for affected VLAN.",
      "Standby for orders. Awaiting intel confirmation.",
      "Drafting mandatory breach notification as per GDPR Art. 33.",
      "System health checks running.",
      "API Gateway P95 latency exceeds threshold.",
      "CPU utilization critical on DB cluster.",
      "Unusual file modification patterns on server FS01.",
      "User reported suspicious email attachment.",
    ];

    const type = logTypes[Math.floor(Math.random() * logTypes.length)];
    const source = sources[Math.floor(Math.random() * sources.length)];
    const message = messages[Math.floor(Math.random() * messages.length)];

    li.classList.add(`log-${type}`);
    li.innerHTML = `<span class="log-timestamp">${timestamp}</span> <span class="log-source">${source}:</span> ${message}`;

    logFeedElement.prepend(li);
    gsap.fromTo(
      li,
      { opacity: 0, x: -15 },
      { opacity: 1, x: 0, duration: 0.5, ease: "power2.out" }
    );

    const maxLogs = 40;
    if (logFeedElement.children.length > maxLogs) {
      const lastChild = logFeedElement.lastElementChild;
      gsap.to(lastChild, {
        opacity: 0,
        height: 0,
        margin: 0,
        padding: 0,
        duration: 0.3,
        onComplete: () => lastChild.remove(),
      });
    }
  }

  function startDashboardSimulation() {
    if (simTimerInterval) clearInterval(simTimerInterval);
    if (logInterval) clearInterval(logInterval);

    simTimerInterval = setInterval(() => {
      currentSimTime++;
      if (simTimeElement)
        simTimeElement.textContent = formatTime(currentSimTime);
      updateDashboardStatus(); // Update stats less frequently than logs
    }, 1000);

    logInterval = setInterval(addSimulatedLogEntry, 2000); // Add logs every 2 seconds
  }

  // --- Testimonial Slider (Swiper JS) ---
  if (typeof Swiper !== "undefined") {
    try {
      const swiper = new Swiper(".testimonials-slider", {
        loop: true,
        slidesPerView: 1,
        spaceBetween: 30,
        autoplay: { delay: 7000, disableOnInteraction: true }, // Longer delay, stops on interaction
        pagination: { el: ".swiper-pagination", clickable: true },
        watchOverflow: true, // Disables features if not enough slides
        breakpoints: {
          768: { slidesPerView: 2, spaceBetween: 30 },
          1024: { slidesPerView: 2, spaceBetween: 40 }, // Keeping 2 for better readability unless content is very short
        },
        a11y: {
          // Accessibility
          prevSlideMessage: "Previous testimonial",
          nextSlideMessage: "Next testimonial",
        },
      });
    } catch (e) {
      console.error("Error initializing Swiper:", e);
    }
  } else {
    console.warn("Swiper library not loaded.");
  }

  // --- Modal Logic ---
  const modalTriggers = document.querySelectorAll("[data-modal-target]");
  const modals = document.querySelectorAll(".modal");
  const modalCloses = document.querySelectorAll(".modal-close");

  modalTriggers.forEach((trigger) => {
    trigger.addEventListener("click", (e) => {
      e.preventDefault(); // Prevent default if trigger is a link
      const targetModalId = trigger.dataset.modalTarget;
      const targetModal = document.getElementById(targetModalId);
      if (targetModal) {
        targetModal.classList.add("active");
        body.style.overflow = "hidden";
      }
    });
  });

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove("active");
    if (!document.querySelector(".modal.active")) {
      // Only restore scroll if no other modals are open
      body.style.overflow = "";
    }
  }

  modalCloses.forEach((button) => {
    button.addEventListener("click", () => {
      closeModal(button.closest(".modal"));
    });
  });

  modals.forEach((modal) => {
    modal.addEventListener("click", (e) => {
      // Close only if clicking the modal backdrop itself (the .modal element)
      if (e.target === modal) {
        closeModal(modal);
      }
    });
  });

  // --- Footer Year ---
  const yearElement = document.getElementById("currentYearFooter");
  if (yearElement) {
    yearElement.textContent = new Date().getFullYear();
  }
}); // End DOMContentLoaded
