$.liveSetup('inline_edit', function(event, context, $$) {
	$$('.inline-edit', context)
		.on('ajaxify-submit-done', function(e, $submit, data) {
			if (data && data.data) {
				var $data = $(data.data),
					$this = $(this),
					$rel = $($(this).attr('rel'));
				$rel.html($data);
				$data.liveSetup();

				$rel.show();
				$this.hide();
			}
		})
		.on('ajaxify-submit-error', function(e, $submit, data) {
			if (data && data.data) {
				var $target = $submit.closest('.inline-edit'),
					$data = $(data.data);
				$target.html($data);
				$data.liveSetup();
			}
		})
		.on('lazyloader-done', function(e, $submit, data) {
			var rel = $(this).attr('rel');

			$(rel).hide();

			$(this)
				.show()
				.find('input:visible:not([disabled], [type=hidden]), select:visible:not([disabled]), textarea:visible:not([disabled]), button:visible:not([disabled])')
				.first().focus();
		});

	$$('[data-provide="cancel-edition"]', context).on('click', function(){
		var data = $(this).closest('.inline-edit'),
			rel = $(data).attr('rel');

		data.removeClass("loaded lazy-loaded");
		$(rel).show();
		$(data).hide();
		return false;
	});
});