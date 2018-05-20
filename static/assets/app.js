/**
 * App module
 */
var app = angular.module("whisper", []);

/**
 * App config
 */
app.config(function ($locationProvider, $compileProvider, $interpolateProvider) {
  $locationProvider.hashPrefix("");
  $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|file|sms|tel):/);
  $interpolateProvider.startSymbol('[[');
  $interpolateProvider.endSymbol(']]');
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
  }
});

/**
 * Main controller
 */
app.controller("MainController", function () {

  var vm = this;

  vm.constructor = function () {

    vm.hi = "wow";
  };

  vm.constructor();
});

/**
 * Index controller
 */
app.controller("IndexController", function (UTILS, SETTING, $scope) {

  var vm = this;

  /**
   * @type {number}
   */
  vm.currentRoom = 0;

  vm.constructor = function () {

    // Check notification
    if (Notification.permission !== "denied") {
      Notification.requestPermission();
    }

    // Correctly decide between ws:// and wss://
    vm.ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    vm.ws_path = vm.ws_scheme + '://' + window.location.host + "/chat/stream/";
    vm.socket = new ReconnectingWebSocket(vm.ws_path);

    // Handle incoming messages
    vm.socket.onmessage = function (message) {
      // Decode the JSON
      console.log("Got websocket message " + message.data);
      var data = JSON.parse(message.data);
      // Handle errors
      if (data.error) {
        alert(data.error);
        return;
      }
      // Handle joining
      if (data.join) {
        console.log("Joining room " + data.join);
        var roomdiv = $(
            "<div class='room' id='room-" + data.join + "'>" +
            "<h2>" + data.title + "</h2>" +
            "<div class='messages'></div>" +
            "<form><input><button>Send</button></form>" +
            "</div>"
        );
        // Hook up send button to send a message
        roomdiv.find("form").on("submit", function () {
          vm.socket.send(JSON.stringify({
            "command": "send",
            "room": data.join,
            "message": roomdiv.find("input").val()
          }));
          roomdiv.find("input").val("");
          return false;
        });
        $("#chats").append(roomdiv);
        // Handle leaving
      } else if (data.leave) {
        console.log("Leaving room " + data.leave);
        $("#room-" + data.leave).remove();
        // Handle getting a message
      } else if (data.message || data.msg_type != 0) {
        var msgdiv = $("#room-" + data.room + " .messages");
        var ok_msg = "";
        // msg types are defined in chat/settings.py
        // Only for demo purposes is hardcoded, in production scenarios, consider call a service.
        switch (data.msg_type) {
          case UTILS.MESSAGE_TYPE.NORMAL:
            // Message
            ok_msg = "<div class='message'>" +
                "<span class='username'>" + data.username + "</span>" +
                "<span class='body'>" + data.message + "</span>" +
                "</div>";

            if (SETTING.USER.USERNAME != data.username) {
              vm.notify(data.username + ": " + data.message);
            }

            break;
          case UTILS.MESSAGE_TYPE.WARNING:
            // Warning / Advice messages
            ok_msg = "<div class='contextual-message text-warning'>" + data.message + "</div>";
            break;
          case UTILS.MESSAGE_TYPE.ALERT:
            // Alert / Danger messages
            ok_msg = "<div class='contextual-message text-danger'>" + data.message + "</div>";
            break;
          case UTILS.MESSAGE_TYPE.MUTE:
            // "Muted" messages
            ok_msg = "<div class='contextual-message text-muted'>" + data.message + "</div>";
            break;
          case UTILS.MESSAGE_TYPE.JOIN:
            // User joined room
            ok_msg = "<div class='contextual-message text-muted'>" + data.username + " joined the room!" +
                "</div>";
            break;
          case UTILS.MESSAGE_TYPE.LEAVE:
            // User left room
            ok_msg = "<div class='contextual-message text-muted'>" + data.username + " left the room!" + "</div>";
            break;
          default:
            console.log("Unsupported message type!");
            return;
        }
        msgdiv.append(ok_msg);

        msgdiv.scrollTop(msgdiv.prop("scrollHeight"));
      } else {
        console.log("Cannot handle message!");
      }
    };

    /**
     * On socket open
     */
    vm.socket.onopen = function () {

      console.log("Connected to chat socket");

      // Join the last visited room
      if (location.hash) {
        vm.openRoom(parseInt(location.hash.split("#")[1]));
        $scope.$apply();
      }
    };

    /**
     * On socket close
     */
    vm.socket.onclose = function () {
      console.log("Disconnected from chat socket");
    };
  };

  /**
   * Join the room and leave others
   *
   * @param roomId
   */
  vm.openRoom = function (roomId) {

    // Not in any room, join this one
    if (!vm.currentRoom) {
      vm.currentRoom = roomId;
      vm.socket.send(JSON.stringify({
        "command": "join",
        "room": roomId
      }));
      return;
    }

    // Is in this room, leave
    if (vm.currentRoom == roomId) {
      vm.currentRoom = 0;
      vm.socket.send(JSON.stringify({
        "command": "leave",
        "room": roomId
      }));
      return;
    }

    // In another room, leave that one and join again
    vm.openRoom(vm.currentRoom);
    vm.openRoom(roomId);
  }

  /**
   * Create and handle notification
   *
   * @param {string} message
   */
  vm.notify = function (message) {

    // Let's check if the browser supports notifications
    if (!("Notification" in window)) {
      alert("This browser does not support desktop notification");
    }

    // Let's check whether notification permissions have already been granted
    else if (Notification.permission === "granted") {
      // If it's okay let's create a notification
      var notification = new Notification(message);
    }

    // Otherwise, we need to ask the user for permission
    else if (Notification.permission !== "denied") {
      Notification.requestPermission(function (permission) {
        // If the user accepts, let's create a notification
        if (permission === "granted") {
          var notification = new Notification(message);
        }
      });
    }
  }

  /**
   * Says if we joined a room or not by if there's a div for it
   *
   * @param {number} roomId
   * @returns {boolean}
   */
  vm.inRoom = function (roomId) {
    return $("#room-" + roomId).length > 0;
  };

  vm.constructor();
});
