/**
 * jQuery liveSetup plugin v1.0
 * @author German M. Bravo (Kronuz) [german DOT mb AT deipi DOT com]
 * @requires jQuery
 *
 * Copyright (c) 2014, deipi.com LLC
 * All rights reserved.
 *
 * Date: 2014-4-10
 */
(function($) {

	var $$ = function(selector, context) {
		var ret = $(selector, context);
		if (context) {
			ret = ret.add($(context).filter(selector));
		}
		return ret;
	};

	$.liveSetup = $.fn.liveSetup = function(namespaces, fn, run) {
		// receives a function and an optional boolean to
		// also request the function to be run.
		if ($.isFunction(namespaces)) {
			run = fn;
			fn = namespaces;
			namespaces = 'liveSetup';
		} else if (namespaces) {
			namespaces = 'liveSetup' + '.' + namespaces.split(' ').join(' liveSetup.');
		} else {
			namespaces = 'liveSetup';
		}
		if (fn && $.isFunction(fn)) {
			$(window).on(namespaces, fn);
			if (run || run === undefined) {
				$(function() {
					fn(null, document, $$);
				});
			}
		} else {
			namespaces = namespaces.split(' ');
			return this.each(function() {
				for (var i in namespaces) {
					$(window).trigger(namespaces[i], [this, $$]);
				}
			});
		}
	};

})(jQuery);
