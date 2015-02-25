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

	function get_target(target, $element) {
		switch(target) {
			case 'me':
				return $($element);
			case 'parent':
				return $($element.parent());
			case 'next':
				return $($element.next());
			case 'prev':
				return $($element.prev());
			default:
				return $(target);
		}
	}

	var LazyLoader = function(element, options) {
		this.$element = $(element);

		this.options = $.extend(
			{},
			LazyLoader.DEFAULTS,
			options
		);

		var $config = $(this.$element.closest('[action]'));

		this.target = $config.data('target');

		this.action = $config.attr('action');
		this.method = $config.attr('method');
		this.prefix = $config.data('prefix') || '';
		this.source = $config.data('source');
		this.omit_insertion = $config.data('omit-insertion') !== undefined;
		this.loaded = 'lazy-loaded ' + ($config.data('loaded') || 'loaded');
		this.ignore_loaded = $config.data('ignore-loaded') !== undefined;
		this.collapse_class = $config.data('collapse-class');

		this.subprefix = $config.data('subprefix');
		this.replacewith = $config.data('replacewith');
	};

	LazyLoader.prototype.load = function() {
		var self = this,
			$target = get_target(this.target, this.$element),
			prefix = this.prefix,
			subprefix = this.subprefix,
			replacewith = this.replacewith,
			loaded = this.loaded,
			collapse_class = this.collapse_class;
		if (!$target.length) {
			console.error("No target for lazy loader!");
		}
		if (!collapse_class || $target.hasClass(collapse_class)) {
			if (!this.ignore_loaded && $target.hasClass(loaded)) {
				$target.removeClass(collapse_class);
				$target.trigger('lazyloader-done', [this.$element]);
			} else {
				$target.trigger('lazyloader-processing', [this.$element]);
				$.ajax({
					url: this.action,
					type: this.method,
					data: this.source && $('input, textarea, select', this.source).serialize(),
					success: function(data, textStatus, jqXHR) {
						var _data = data.data || data;

						if (data.message) {
							announce({
								status: data.status,
								message: data.message,
								settimer: data.settimer
							});
						}

						if (prefix) {
							_data = _data.replace(/__fp__/g, prefix);
						} else {
							_data = _data.replace(/__fp__-/g, prefix);
						}
						if (subprefix && replacewith) {
							var re = new RegExp(subprefix, 'g');
							_data = _data.replace(re, replacewith);
						}
						if (!self.omit_insertion) {
							var $data = $(_data);
							$target.html($data);
							$data.liveSetup();
						}
						$target.removeClass('loaded loaded-edit loaded-detail');
						if (!self.ignore_loaded) {
							$target.removeClass('loaded loaded-edit loaded-detail').addClass(loaded);
						}
						$target.removeClass(collapse_class);
						$target.trigger('lazyloader-done', [self.$element, _data]);
					},
					error: function(jqXHR, textStatus, errorThrown) {
						var message = jqXHR.status + ' - ' + (errorThrown || "Connection Error!");
						announce({
							status: 'ERR',
							message: message
						});
						$target.trigger('lazyloader-error', [self.$element]);
					}
				});
			}
		} else {
			$target.removeClass('loaded loaded-edit');
			$target.addClass(collapse_class);
			$target.trigger('lazyloader-done', [this.$element]);
		}
	};

	LazyLoader.prototype.submit = function() {
		var self = this,
			$target = get_target(this.target, this.$element),
			collapse_class = this.collapse_class,
			subprefix = this.subprefix,
			replacewith = this.replacewith,
			data;

		data = $('input, textarea, select', this.source).serialize();

		if (subprefix && replacewith) {
			var re = new RegExp(subprefix, 'g');
			data = data.replace(re, replacewith);
		}

		$target.trigger('ajaxify-submit-processing', [this.$element]);
		$.ajax({
			url: this.action,
			type: this.method,
			data: data,
			success: function(data, textStatus, jqXHR) {
				if (data.message) {
					announce({
						status: data.status,
						message: data.message,
						settimer: data.settimer
					});
				}

				if (data.status === 'OK') {
					if (collapse_class) {
						$target.addClass(collapse_class);
					}
					$target.removeClass('loaded loaded-edit loaded-detail');
					$target.trigger('ajaxify-submit-done', [self.$element, data]);
				} else {
					$target.trigger('ajaxify-submit-error', [self.$element, data]);
				}
			},
			error: function(jqXHR, textStatus, errorThrown) {
				var message = jqXHR.status + ' - ' + (errorThrown || "Connection Error!");
				announce({
					status: 'ERR',
					message: message
				});
				$target.trigger('ajaxify-submit-error', [self.$element]);
			}
		});
	};

	/* Setup plugin defaults */
	LazyLoader.DEFAULTS = {};

	$.fn.lazyloader = function(option) {
		return this.each(function() {
			var $this = $(this),
				data = $this.data('lazyloader'),
				options = typeof option === 'object' && option;

			if (!data) $this.data('lazyloader', (data = new LazyLoader(this, options)));
			if (typeof option === 'string') data[option]();
		});
	};

	$(document).on('click.dub.lazyloader', '[data-provide="lazy-loader"]', function(e) {
		e.preventDefault();
		e.stopPropagation();
		$(this).lazyloader('load');
	});

	$(document).on('click.dub.lazyloader', '.lazy-loaded [type="submit"], [data-provide="ajaxify-submit"]', function(e) {
		e.preventDefault();
		e.stopPropagation();
		$(this).lazyloader('submit');
	});

})(jQuery);
