/**
 * Helpers
 */
var helpers = {
  randomIndex: function (list) {
    return list[Math.floor(Math.random() * list.length)];
  }
};

/**
 * App module
 */
var app = angular.module("whisper", []);
      /**
       * Simple Web RTC
       */
      webrtc = new SimpleWebRTC({
        url: "https://signals.savandbros.com/",
        // the id/element dom element that will hold "our" video
        localVideoEl: "local-video",
        // the id/element dom element that will hold remote videos
        remoteVideosEl: "remote-videos",
        // immediately ask for camera access
        autoRequestMedia: true
      });
      webrtc.on("readyToCall", function () {
        webrtc.joinRoom("test");
      });
/**
 * App config
 */
app.config(function ($locationProvider, $compileProvider, $interpolateProvider) {
  $locationProvider.hashPrefix("");
  $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|file|sms|tel):/);
  $interpolateProvider.startSymbol("[[");
  $interpolateProvider.endSymbol("]]");
});

/**
 * App constant
 */
app.constant("UTILS", {
  MESSAGE_TYPE: {
    NORMAL: 0,
    WARNING: 1,
    ALERT: 2,
    MUTE: 3,
    JOIN: 4,
    LEAVE: 5
  },
  MESSAGE_COLOR: [
    "hsl(0, 79%, 66%)",
    "hsl(30, 79%, 66%)",
    "hsl(100, 79%, 66%)",
    "hsl(165, 79%, 66%)",
    "hsl(175, 79%, 66%)",
    "hsl(219, 79%, 66%)",
    "hsl(250, 79%, 66%)",
    "hsl(281, 79%, 66%)",
    "hsl(330, 79%, 66%)"
  ]
});

/**
 * Convert factgory
 */
app.factory("Convert", function ($sce) {
  return {
    tools: {
      hasElement: function (text, element) {
        return angular.element(document.createElement("text")).html(text).has(element).length > 0;
      }
    },
    link: function (text) {
      return linkifyStr(text);
    },
    bold: function (text) {
      return text.replace(/\*(.*?)\*/g, "<b>$1</b>");
    },
    italic: function (text) {
      return text.replace(/\_(.*?)\_/g, "<em>$1</em>");
    },
    strike: function (text) {
      return text.replace(/\~(.*?)\~/g, "<s>$1</s>");
    },
    code: function (text) {
      return text.replace(/\`(.*?)\`/g, "<code>$1</code>");
    },
    all: function (text) {
      if (text) {
        output = text;
        output = this.link(output);
        output = this.bold(output);
        output = this.italic(output);
        output = this.strike(output);
        output = this.code(output);
        return $sce.trustAsHtml(output);
      }
    }
  }
});

/**
 * Room class
 */
app.service("Room", function ($rootScope) {
  return function (data) {
    var self = this;
    self.id = data.id;
    self.title = data.title;
    self.messages = [];
    self.joined = false;
    self.message = function (message) {
      self.messages.push(message);
    }
    self.join = function (socket) {
      if (self.joined) {
        return;
      }
      self.joined = true;
      socket.send(JSON.stringify({
        "command": "join",
        "room": self.id
      }));
    };
  };
});

/**
 * Message class
 */
app.service("Message", function (SETTING, UTILS, Convert, $filter) {
  return function (data) {
    var self = this;
    self.rawMessage = data.message;
    self.username = data.username;
    self.color = helpers.randomIndex(UTILS.MESSAGE_COLOR);
    self.kind = data.msg_type;
    self.message = Convert.all(self.rawMessage);
    self.date = new Date();
    self.getDate = function () {
      var format = "HH:mm a"
      if ((new Date()) - self.date > new Date(new Date() - 86400000)) {
        format = null;
      }
      return $filter("date")(self.date, format);
    };
    self.isOwn = function () {
      return self.username === SETTING.USER.USERNAME;
    };
  };
});

/**
 * Main controller
 */
app.controller("MainController", function () {

  var vm = this;

  vm.constructor = function () {};

  vm.constructor();
});

/**
 * Index controller
 */
app.controller("IndexController", function (UTILS, SETTING, VIEW, PATH, Room, Message, $scope, $timeout, $http) {

  var vm = this;

  vm.constructor = function () {

    /**
     * @type {Array<object>}
     */
    vm.chatForm = {
      /**
       * @type {string}
       */
      message: "",
    };

    /**
     * @type {Array<Room>}
     */
    vm.rooms = [];

    /**
     * Current room instance
     * @type {Room}
     */
    vm.room = null;

    /**
     * @type {boolean}
     */
    vm.inVideoCall = false;

    /**
     * @type {boolean}
     */
    vm.isFocused = true;

    /**
     * @type {object}
     */
    vm.dropup = {
      /**
       * @type {boolean}
       */
      dropup: false,
      /**
       * @type {boolean}
       */
      emojis: false
    };

    /**
     * Get rooms
     */
    angular.forEach(VIEW.ROOMS, function (room) {
      vm.rooms.push(new Room(room));
    });

    /**
     * Check notification permission
     */
    if (Notification.permission !== "denied") {
      Notification.requestPermission();
    }

    /**
     * Correctly decide between ws:// and wss://
     */
    vm.ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    vm.ws_path = vm.ws_scheme + "://" + window.location.host + "/chat/stream/";
    vm.socket = new ReconnectingWebSocket(vm.ws_path);

    /**
     * On socket message
     */
    vm.socket.onmessage = function (messageData) {
      var data = JSON.parse(messageData.data);
      var message = new Message(data);
      var room = data.room == vm.room.id ? vm.room : null;
      var fromUser = data.username === SETTING.USER.USERNAME;

      // Not from this room, find the room
      if (!room) {
        for (var i in vm.rooms) {
          if (vm.rooms[i].id === data.room) {
            room = vm.rooms[i];
          }
        }
      }

      console.log("New socket message", data);

      // Add to room messages
      if (room) {

        // Don't add own normal messages (already added to prevent socket delay)
        if (!message.isOwn() || message.kind !== UTILS.MESSAGE_TYPE.NORMAL) {
          room.message(message);
        }

        // Scroll to bottom
        var wrapper = angular.element("#chat-messages");
        wrapper.stop().animate({
          scrollTop: wrapper.prop("scrollHeight")
        });
      }

      // Notify
      if (!fromUser) {
        vm.notify(room, message);
      }

      // Handle error
      if (data.error) {
        alert(data.error);
      }

      // Update template
      $scope.$apply();
    };

    /**
     * On socket open
     */
    vm.socket.onopen = function () {

      console.log("Connected to chat socket");

      // Join the last visited room
      if (location.hash) {
        var index = parseInt(location.hash.split("#")[1]);
        if (vm.rooms[index]) {
          vm.openRoom(vm.rooms[index]);
          $scope.$apply();
        }
      }
    };

    /**
     * On socket close
     */
    vm.socket.onclose = function () {
      console.log("Disconnected from chat socket");
    };

    /**
     * Get emojis
     */
    $http.get(PATH.EMOJIS).then(function (data) {
      $scope.emojis = data.data;
    });
  };

  /**
   * @param {Room} room
   */
  vm.openRoom = function (room) {

    // Alrady in this room
    if (vm.room && vm.room.id == room.id) {
      return;
    }

    // Open this room (join if not already in)
    vm.room = room;
    vm.room.join(vm.socket);
  };

  /**
   * Send a message to current room
   *
   * @param {string} message
   */
  vm.message = function () {

    // Validate message
    if (!vm.chatForm.message.length) {
      return;
    }

    // Send message
    vm.socket.send(JSON.stringify({
      "command": "send",
      "room": vm.room.id,
      "message": vm.chatForm.message
    }));

    // Add to messages (don't wait for socket)
    vm.room.message(new Message({
      message: vm.chatForm.message,
      username: SETTING.USER.USERNAME,
      msg_type: UTILS.MESSAGE_TYPE.NORMAL
    }));

    // Clear message input
    vm.chatForm.message = "";

    // Close dropup
    vm.dropup.dropup = vm.dropup.emojis = false;
  };

  /**
   * Create and handle notification
   *
   * @param {Room} room
   * @param {string} message
   */
  vm.notify = function (room, message) {

    // Don't notify if focused on window and is in the same room
    if (vm.isFocused && room && room.id == vm.room.id) {
      return;
    }

    // Validate message
    if (typeof message.message === "undefined") {
      return;
    }

    // Let's check if the browser supports notifications
    if (!("Notification" in window)) {
      alert("This browser does not support desktop notification");
    }

    // Let's check whether notification permissions have already been granted
    else if (Notification.permission === "granted") {
      // If it's okay let's create a notification
      var notification = new Notification(message.message);
    }

    // Otherwise, we need to ask the user for permission
    else if (Notification.permission !== "denied") {
      Notification.requestPermission(function (permission) {
        // If the user accepts, let's create a notification
        if (permission === "granted") {
          var notification = new Notification(message.message);
        }
      });
    }
  };

  /**
   * Insert a text into the chat input in the current position
   *
   * @param {string} text
   */
  vm.insertToMessage = function (text) {
    var element = angular.element("#focus")[0];
    var pos = element.selectionStart;
    var dest = angular.copy(vm.chatForm.message);
    vm.chatForm.message = dest.substr(0, pos) + text + dest.substr(pos);
    vm.focusInput(2);
  };

  /**
   * Toggle dropup with emojis
   */
  vm.toggleEmojis = function () {
    vm.focusInput();
    vm.dropup.dropup = vm.dropup.emojis = !vm.dropup.dropup;
  };

  /**
   * Focus input on cursor position
   */
  vm.focusInput = function (offset) {
    var input = angular.element("#focus")[0];
    var posStart = input.selectionEnd;
    var posEnd = input.selectionEnd;
    input.focus();
    if (offset) {
      $timeout(function () {
        input.selectionStart = posStart + offset;
        input.selectionEnd = posEnd + offset;
      }, 100);
    }
    vm.isFocused = true;
  };

  /**
   * Join video call
   */
  vm.joinVideoCall = function () {

    // Toggle call
    vm.inVideoCall = !vm.inVideoCall;

    // Not in any video call
    if (vm.inVideoCall) {
      /**
       * Simple Web RTC
       */
      vm.webrtc = new SimpleWebRTC({
        // the id/element dom element that will hold "our" video
        localVideoEl: "local-video",
        // the id/element dom element that will hold remote videos
        remoteVideosEl: "remote-videos",
        // immediately ask for camera access
        autoRequestMedia: true
      });
      vm.webrtc.on("readyToCall", function () {
        vm.webrtc.joinRoom(vm.room.id);
      });
    }

    // In a video call, handgup
    else {
      // vm.webrtc.hangUp();
    }
  }

  /**
   * Handle focus of window
   */
  angular.element(window).on("load resize", function () {
    var height = window.innerHeight - 234;
    if (window.innerWidth <= 991) {
      height += 120;
    }
    angular.element("#chat-messages").height(height);
    angular.element("#messages-wrapper").css("max-height", angular.element("#chat-messages").height());
  });

  /**
   * Handle focus of window and chat input
   */
  angular.element(window).on("load focus", vm.focusInput);

  /**
   * Handle losing focus of window
   */
  angular.element(window).on("blur", function () {
    vm.isFocused = false;
  });

  vm.constructor();
});
