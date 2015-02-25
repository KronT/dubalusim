/**
 * Dubalu Framework
 * ~~~~~~~~~~~~~~~~
 *
 * :author: Dubalu Framework Team. See AUTHORS.
 * :copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
 * :license: See LICENSE for license details.
 *
*/
(function(window) {
	'use strict';

	window.asyncLoadScript = function(src) {
		var update = function() {
			var s = document.createElement('script');
			s.src = src;
			s.type = "text/javascript";
			s.async = true;
			var insertAt = document.getElementsByTagName('script')[0];
			return insertAt.parentNode.insertBefore(s, insertAt);
		};
		if (window.attachEvent !== undefined) {
			window.attachEvent('onload', update);
		} else {
			window.addEventListener('load', update, false);
		}
	};
})(window);
