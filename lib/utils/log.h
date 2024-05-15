/*
 * Copyright 2022 Max Planck Institute for Software Systems, and
 * National University of Singapore
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef UTILS_LOG_H_
#define UTILS_LOG_H_

#include <stdio.h>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <string_view>
#include <unordered_map>
#include <utility>

namespace sim_log {

#define SIMLOG 1

#define SIMLOG_ERROR 1
#define SIMLOG_WARN 2
#define SIMLOG_INFO 3
#define SIMLOG_OFF 4

enum LogLevel : int {
  off = SIMLOG_OFF,
  info = SIMLOG_INFO,
  warn = SIMLOG_WARN,
  error = SIMLOG_ERROR
};

class Log;
using LogPtT = std::unique_ptr<Log>;

class Log {
 public:
  FILE *file_ = nullptr;
  const bool is_file_ = false;

  explicit Log(FILE *file) : file_(file), is_file_(false) {
  }

  Log(FILE *file, bool is_file) : file_(file), is_file_(is_file) {
  }

  ~Log() {
    if (file_ != nullptr && is_file_) {
      fclose(file_);
    }
  }

  static LogPtT createLog() {
    FILE *out;
    out = stdout;
    return std::make_unique<Log>(out);
  }

  static LogPtT createLog(FILE* out, bool file) {
    if (out == nullptr) {
        fprintf(stderr, "error: FILE* is null, fallback to stdout logging\n");
        out = stdout;
    }
    return std::make_unique<Log>(out, file);
  }

  static LogPtT createLog(const char *file_path) {
    if (file_path == nullptr) {
      fprintf(stderr, "error: file_path is null, fallback to stdout logging\n");
      return sim_log::Log::createLog();
    }

    FILE *file = fopen(file_path, "w");
    return createLog(file, true);
  }
};

class LogRegistry {
  const std::unordered_map<LogLevel, const char *> level_names_{
      {LogLevel::off, "off"},
      {LogLevel::info, "info"},
      {LogLevel::warn, "warn"},
      {LogLevel::error, "error"}};

  LogLevel level_ = LogLevel::info;

 public:
  LogLevel &GetLevel() {
    return level_;
  }

  void SetLogLevel(LogLevel level) {
    level_ = level;
  }

  const char *GetRepr(LogLevel level) const {
    auto it = level_names_.find(level);
    if (it == level_names_.end()) {
      static const char *undef{"undefined"};
      return undef;
    }
    return it->second;
  }
};

class Logger {
 private:
  inline bool ShouldLog(LogLevel level) {
    auto &registry = Logger::GetRegistry();
    return level >= registry.GetLevel() &&
           registry.GetLevel() != LogLevel::off;
  }

  template <typename... Args>
  inline void log_internal(LogLevel level, FILE *out, const char *format,
                           Args... args) {
    if (!ShouldLog(level)) {
      return;
    }
    fprintf(out, "%s: ", GetRegistry().GetRepr(level));
    fprintf(out, format, args...);
    fflush(out);
  }

  inline void log_internal(LogLevel level, FILE *out, const char *to_print) {
    if (!ShouldLog(level)) {
      return;
    }
    fprintf(out, "%s: ", GetRegistry().GetRepr(level));
    fprintf(out, "%s", to_print);
    fflush(out);
  }

  Logger() = default;

  ~Logger() = default;

 public:
  static Logger &GetLogger() {
    static Logger logger;
    return logger;
  }

  static LogRegistry &GetRegistry() {
    static LogRegistry registry;
    return registry;
  }

  template <typename... Args>
  inline void log_stdout_f(LogLevel level, const char *format,
                           const Args &...args) {
    this->log_internal(level, stdout, format, args...);
  }

  inline void log_stdout(LogLevel level, const char *to_print) {
    this->log_internal(level, stdout, to_print);
  }

  template <typename... Args>
  void log_f(LogLevel level, LogPtT &log, const char *format,
             const Args &...args) {
    if (log->file_ == nullptr) {
      this->log_stdout(level, "log file is null. it should not be!\n");
      this->log_stdout_f(level, format, args...);
      return;
    }
    this->log_internal(level, log->file_, format, args...);
  }

  void log(LogLevel level, LogPtT &log, const char *to_print) {
    if (log->file_ == nullptr) {
      this->log_stdout(level, "log file is null. it should not be!\n");
      this->log_stdout(level, to_print);
      return;
    }
    this->log_internal(level, log->file_, to_print);
  }
};

#ifdef SIMLOG

template <typename... Args>
inline void LogInfo(LogPtT &log, const char *fmt, Args &&...args) {
  sim_log::Logger::GetLogger().log_f(LogLevel::info, log, fmt,
                                     std::forward<Args>(args)...);
}

inline void LogInfo(LogPtT &log, const char *msg) {
  sim_log::Logger::GetLogger().log(LogLevel::info, log, msg);
}

template <typename... Args>
inline void LogInfo(const char *fmt, Args &&...args) {
  sim_log::Logger::GetLogger().log_stdout_f(LogLevel::info, fmt,
                                            std::forward<Args>(args)...);
}

inline void LogInfo(const char *msg) {
  sim_log::Logger::GetLogger().log_stdout(LogLevel::info, msg);
}

template <typename... Args>
inline void LogWarn(LogPtT &log, const char *fmt, Args &&...args) {
  sim_log::Logger::GetLogger().log_f(LogLevel::warn, log, fmt,
                                     std::forward<Args>(args)...);
}

inline void LogWarn(LogPtT &log, const char *msg) {
  sim_log::Logger::GetLogger().log(LogLevel::warn, log, msg);
}

template <typename... Args>
inline void LogWarn(const char *fmt, Args &&...args) {
  sim_log::Logger::GetLogger().log_stdout_f(LogLevel::warn, fmt,
                                            std::forward<Args>(args)...);
}

inline void LogWarn(const char *msg) {
  sim_log::Logger::GetLogger().log_stdout(LogLevel::warn, msg);
}

template <typename... Args>
inline void LogError(LogPtT &log, const char *fmt, Args &&...args) {
  sim_log::Logger::GetLogger().log_f(LogLevel::error, log, fmt,
                                     std::forward<Args>(args)...);
}

inline void LogError(LogPtT &log, const char *msg) {
  sim_log::Logger::GetLogger().log(LogLevel::error, log, msg);
}

template <typename... Args>
inline void LogError(const char *fmt, Args &&...args) {
  sim_log::Logger::GetLogger().log_stdout_f(LogLevel::error, fmt,
                                            std::forward<Args>(args)...);
}

inline void LogError(const char *msg) {
  sim_log::Logger::GetLogger().log_stdout(LogLevel::error, msg);
}

#else

template <typename... Args>
inline void LogInfo(LogPtT &log, const char *fmt, Args &&...args) {
}

inline void LogInfo(LogPtT &log, const char *msg) {
}

template <typename... Args>
inline void LogInfo(const char *fmt, Args &&...args) {
}

inline void LogInfo(const char *msg) {
}

template <typename... Args>
inline void LogWarn(LogPtT &log, const char *fmt, Args &&...args) {
}

inline void LogWarn(LogPtT &log, const char *msg) {
}

template <typename... Args>
inline void LogWarn(const char *fmt, Args &&...args) {
}

inline void LogWarn(const char *msg) {
}

template <typename... Args>
inline void LogError(LogPtT &log, const char *fmt, Args &&...args) {
}

inline void LogError(LogPtT &log, const char *msg) {
}

template <typename... Args>
inline void LogError(const char *fmt, Args &&...args) {
}

inline void LogError(const char *msg) {
}

#endif

}  // namespace sim_log

#endif  // UTILS_LOG_H_
