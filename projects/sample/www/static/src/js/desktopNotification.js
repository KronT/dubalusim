/**
 * Dubalu Framework
 * ~~~~~~~~~~~~~~~~
 *
 * :author: Dubalu Framework Team. See AUTHORS.
 * :copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
 * :license: See LICENSE for license details.
 *
*/
(function(window, $) {
	/*
		Usage Example:

		First request permission as soon as the user does anything:
			$(function() {
				$('body').on('click.notification', function() {
					if (!$(this).hasClass('backdrop-shown')) {
						$.desktopNotification.requestPermission();
						$('body').off('.notification');
					}
				});
			});


		Then send desktop notifications using:
			$.desktopNotification.sendNotification(
				'Title', {
					icon: '/static/img/zopim-banner.png',
					body: 'Message'
				}
			);

	*/
	'use strict';

	var permission = null,
		webkitPermissions = ['granted', 'default', 'denied'];


	function checkPermission() {
		// Let's check if the browser supports notifications
		if (!desktopNotification.isSupported) {
			return;
		}

		// If the user is okay, let's create a notification
		if (desktopNotification.permission !== null) {
			return desktopNotification.permission;
		}

		var permission;
		if (window.webkitNotifications) {
			permission = webkitPermissions[window.webkitNotifications.checkPermission()];
		} else {
			if (window.Notification) {
				if (typeof window.Notification.permissionLevel === 'function') {
					permission = window.Notification.permissionLevel();
				} else {
					if (window.Notification.permission) {
						permission = window.Notification.permission;
					}
				}
			}
		}
		desktopNotification.permission = permission;
		return permission;
	}

	function requestPermission(callback) {
		// Let's check if the browser supports notifications
		if (!desktopNotification.isSupported) {
			return;
		}

		var _callback = function(permission) {
			desktopNotification.permission = permission;
			if ($.isFunction(callback)) callback(permission);
		};

		// Otherwise, we need to ask the user for permission
		// Note, Chrome does not implement the permission static property
		// So we have to check for NOT 'denied' instead of 'default'
		if (checkPermission() !== desktopNotification.PERMISSIONS.DENIED) {
			if (window.webkitNotifications && window.webkitNotifications.requestPermission) {
				window.webkitNotifications.requestPermission(_callback);
			} else {
				if (window.Notification && window.Notification.requestPermission) {
					window.Notification.requestPermission(_callback);
				}
			}
		} else {
			_callback(checkPermission());
		}
	}

	function createNotification(title, message) {
		var item;
		if (window.webkitNotifications) {
			item = window.webkitNotifications.createNotification(message.icon, title, message.body);
			item.show();
		} else {
			if (window.Notification) {
				item = new window.Notification(title, {
					icon: message.icon || "",
					body: message.body || "",
					tag: message.tag || ""
				});
			}
		}
		item.cancel = item.cancel || item.close;
		item.cancel = $.isFunction(item.cancel) ? item.cancel : function() {};
		return item;
	}

	function sendNotification(title, message) {
		// Let's check if the browser supports notifications
		if (!desktopNotification.isSupported) {
			return;
		}

		// Let's check if the user is okay to get some notification
		if (checkPermission() === desktopNotification.PERMISSIONS.DENIED) {
			return;
		}

		// If the user is okay, let's create a notification
		if (checkPermission() !== desktopNotification.PERMISSIONS.GRANTED) {
			desktopNotification.requestPermission(function() {
				createNotification(title, message);
			});
		} else {
			createNotification(title, message);
		}
	}

	var desktopNotification = {
		PERMISSIONS : {
			DEFAULT: 'default',
			GRANTED: 'granted',
			DENIED: 'denied'
		},
		permission: null,
		isSupported: !!(window.Notification || window.webkitNotifications),
		checkPermission: checkPermission,
		requestPermission: requestPermission,
		createNotification: createNotification,
		sendNotification: sendNotification
	};

	$.desktopNotification = desktopNotification;
})(window, jQuery);
