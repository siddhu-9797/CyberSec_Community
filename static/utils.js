async function apiCall(
  endpoint,
  method = "GET",
  body = null,
  includeAuth = false
) {
  const finalUrl = endpoint.startsWith("/") ? endpoint : "/" + endpoint;

  const options = {
    method: method,
    headers: {
      Accept: "application/json",
    },
  };

  if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const authToken = includeAuth ? localStorage.getItem("accessToken") : null;
  if (includeAuth && authToken) {
    options.headers["Authorization"] = `Bearer ${authToken}`;
  } else if (includeAuth && !authToken) {
  }

  try {
    const response = await fetch(finalUrl, options);

    if (!response.ok) {
      let errorData = {
        error: `HTTP error! Status: ${response.status} ${response.statusText}`,
      };
      try {
        const errorJson = await response.json();
        errorData.detail = errorJson.detail || JSON.stringify(errorJson);
      } catch (e) {
        errorData.detail = response.statusText;
      }

      return null;
    }

    if (response.status === 204) {
      return {};
    }

    try {
      const jsonData = await response.json();
      return jsonData;
    } catch (e) {
      return {
        success: true,
        status: response.status,
        text: await response.text(),
      };
    }
  } catch (error) {
    return null;
  }
}

window.Logger = (() => {
  const Levels = {
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
    ERROR: 4,
    NONE: 5,
  };

  let _currentLevel = Levels.DEBUG;
  let _logToConsole = true;
  let _logBuffer = [];
  const MAX_BUFFER_SIZE = 500;

  function _formatTimestamp(date = new Date()) {
    return date.toISOString();
  }

  function _getLevelName(levelValue) {
    for (const name in Levels) {
      if (Levels[name] === levelValue) {
        return name;
      }
    }
    return "UNKNOWN";
  }

  function _log(level, message, args) {
    if (level < _currentLevel) {
      return;
    }

    const timestamp = _formatTimestamp();
    const levelName = _getLevelName(level);
    const context = args.length > 0 ? args : null;

    const logEntry = {
      timestamp: timestamp,
      level: levelName,
      levelValue: level,
      message: message,
      context: context,
    };

    _logBuffer.push(logEntry);

    if (_logBuffer.length > MAX_BUFFER_SIZE) {
      _logBuffer.shift();
    }

    if (_logToConsole) {
      const consoleArgs = [`[${levelName}] ${message}`];
      if (context) {
        consoleArgs.push(...context);
      }

      switch (level) {
        case Levels.ERROR:
          break;
        case Levels.WARN:
          break;
        case Levels.INFO:
          break;
        case Levels.DEBUG:
        default:
          break;
      }
    }
  }

  return {
    Levels: Levels,

    setLevel: (newLevel) => {
      if (
        typeof newLevel === "number" &&
        newLevel >= Levels.DEBUG &&
        newLevel <= Levels.NONE
      ) {
        _currentLevel = newLevel;
      } else {
      }
    },

    setConsoleOutput: (enabled) => {
      _logToConsole = !!enabled;
    },

    debug: (message, ...args) => {
      _log(Levels.DEBUG, message, args);
    },
    info: (message, ...args) => {
      _log(Levels.INFO, message, args);
    },
    warn: (message, ...args) => {
      _log(Levels.WARN, message, args);
    },
    error: (message, ...args) => {
      _log(Levels.ERROR, message, args);
    },

    dump: (minLevel = Levels.DEBUG) => {
      if (typeof minLevel !== "number") {
        minLevel = Levels.DEBUG;
      }
      const levelName = _getLevelName(minLevel);

      if (_logBuffer.length === 0) {
        return;
      }

      const filteredLogs = _logBuffer.filter(
        (entry) => entry.levelValue >= minLevel
      );

      if (filteredLogs.length === 0) {
        return;
      }

      filteredLogs.forEach((entry) => {
        const time = entry.timestamp.split("T")[1].replace("Z", "");
        const messagePrefix = `[${time}] [${entry.level}] ${entry.message}`;

        let consoleMethod = console.log;
        if (entry.levelValue === Levels.ERROR) consoleMethod = console.error;
        else if (entry.levelValue === Levels.WARN) consoleMethod = console.warn;
        else if (entry.levelValue === Levels.INFO) consoleMethod = console.info;
        else if (entry.levelValue === Levels.DEBUG)
          consoleMethod = console.debug;

        if (entry.context && entry.context.length > 0) {
        } else {
        }
      });
    },

    clear: () => {
      _logBuffer = [];
    },
  };
})();

Logger.setConsoleOutput(false);
