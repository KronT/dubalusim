/**
 * Dubalu Framework
 * ~~~~~~~~~~~~~~~~
 *
 * :author: Dubalu Framework Team. See AUTHORS.
 * :copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
 * :license: See LICENSE for license details.
 *
*/
(function($) {
	'use strict';

	$.fn.fileinputbutton = function(opts) {
		var options = $.extend({}, $.fn.fileinputbutton.defaults, opts),
			$$ = $(this);

		$(document).on('change', '.'+ options.btnClass +' :file', function() {
	        var input = $(this),
	            numFiles = input.get(0).files ? input.get(0).files.length : 1,
	            label = '',
	            names = [];
			for (var i=0; i<numFiles; i++) {
				names[i] = input.get(0).files[i].name;
			}
			label = names.join(', ');

	        input.trigger(options.triggeredEvent, [numFiles, label]);
		});

		$('.' + options.wrapperClass + ' .' + options.btnClass + ' :file').on(options.triggeredEvent, function(event, numFiles, label) {
	        $('input:text', $(this).closest('.' + options.wrapperClass)).val(label);
	    });
		return $$;
    };

	/* Setup plugin defaults */
    $.fn.fileinputbutton.defaults = {
    	triggeredEvent: 'fileselect',
    	btnClass: 'btn-file',
    	wrapperClass: 'input-group'
    };
})(jQuery);
