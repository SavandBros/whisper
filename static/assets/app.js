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

  /**
   * @type {Array<object>}
   */
  vm.chatForm = {
    message: "",
  };

  /**
   * @type {Array<object>}
   */
  vm.messages = [];

  vm.constructor = function () {

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
    vm.ws_path = vm.ws_scheme + '://' + window.location.host + "/chat/stream/";
    vm.socket = new ReconnectingWebSocket(vm.ws_path);

    /**
     * On socket message
     */
    vm.socket.onmessage = function (message) {

      // Add to message list
      var data = JSON.parse(message.data);
      vm.messages.push(data);
      $scope.$apply();

      // Debug
      console.log("New socket message", data);

      // Notify
      if (data.username !== SETTING.USER.USERNAME) {
        vm.notify(data.message);
      }

      // Handle error
      if (data.error) {
        alert(data.error);
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
      "room": vm.currentRoom,
      "message": vm.chatForm.message
    }));

    // Clear message input
    vm.chatForm.message = "";
  };

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
  };

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
