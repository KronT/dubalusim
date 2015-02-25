(function($) {
	$.fn.ladda = function(option) {
		return this.each(function() {
			var $this = $(this),
				data = $this.data('ladda');

			if (!data) $this.data('ladda', (data = Ladda.create(this)));
			if (typeof option === 'string') data[option]();
		});
	};
})(jQuery);