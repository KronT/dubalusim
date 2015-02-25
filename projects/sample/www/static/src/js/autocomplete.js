/*!
 * jQuery autocomplete plugin v1.0
 *
 * Requires Bootstrap Typeahead and Handlebars
 *
 * Copyright 2014, deipi.com LLC
 *
 * Date: 2014-4-10
 */
(function($) {
	/*
	// Available options:
	{
		'key': '<suggestion key (Saved in the hidden input>',
		'prefetch': <Use prefetch. Defaults to 0, pass ttl>,
		'remote': <use remote loading. Defaults to true>
		'bloodhound': {
			'options': {
				<bloodhound options...>
			}
		},
		'typeahead': {
			'options': {
				<typeahead options...>
			}
			'dataset': {
				'name': '<catalog>',
				'displayKey': '<suggestion label key>',
				'templates': {
					'suggestion': '<html template or suggestion template name (country, country-state, country-currency)>',
				},
			},
		},
		'related': ['.<related selector>'],
		'autoFill': {
			#<selector1>: '<suggestion key1>',
			#<selector2>: '<suggestion key2>',
		},
		'triggerOnSelected': True,
		'focus': '.<selector>'
	}
	*/
	var catalogs = {},
		all_suggestions = null;

	function get_or_create_catalog(id, catalog, options, key, prefetch, remote) {
		var autocomplete = catalogs[id],
			_prefetch = prefetch ? {
				prefetch: $.extend({
					ttl: prefetch === true ? undefined : prefetch,
					url: document.urls.autocomplete.replace('__catalog__', catalog)
				}, options.prefetch)
			} : {},
			_remote = remote ? {
				remote: $.extend({
					url: document.urls.autocomplete.replace('__catalog__', catalog) + '?q=%QUERY',
					ajax: {
						cache: false
					}
				}, options.remote)
			} : {};
		if (!autocomplete) {
			autocomplete = new Bloodhound($.extend({
				limit: 20,
				// dupDetector: function(remoteMatch, localMatch) {
				// 	return remoteMatch.label === localMatch.label && remoteMatch[key] === localMatch[key];
				// },
				datumTokenizer: Bloodhound.tokenizers.obj.whitespace(key),
				queryTokenizer: Bloodhound.tokenizers.whitespace
			}, options, _prefetch, _remote));
			autocomplete.initialize();
			catalogs[id] = autocomplete;
		}
		return autocomplete;
	}

	$.fn.autocomplete = function(options) {
		if (all_suggestions === null) {
			all_suggestions = {
				'country': Handlebars.compile('<p><b><i class="flag f32 {{ iso2 }}"></i> {{ label }}</b></p>'),
				'country-state': Handlebars.compile('<p><b>{{ label }}</b> – {{ country }}</p>'),
				'country-currency': Handlebars.compile('<p><b><i class="flag f32 {{ iso2 }}"></i> {{ value }}</b> – {{ label }} ({{ country }})</p>')
			};
		}
		return this.each(function() {
			var $this = $(this),
				opts = $.extend({}, options || {}, $this.data('autocomplete') || {}),
				bloodhound_options = (opts.bloodhound && opts.bloodhound.options) ? opts.bloodhound.options : opts.bloodhound || opts,
				typeahead_options = (opts.typeahead && opts.typeahead.options) ? opts.typeahead.options : opts.typeahead || opts,
				typeahead_dataset = (opts.typeahead && opts.typeahead.dataset) ? opts.typeahead.dataset : opts.typeahead || opts;

			if (!typeahead_dataset.name) {
				console.warn("Autocomplete with no catalog specified!");
				console.log(opts);
				return;
			}

			var templates = {};

			// Setup empty template for Typeahead:
			var empty = typeahead_dataset.templates && typeahead_dataset.templates.empty,
				header = typeahead_dataset.templates && typeahead_dataset.templates.header,
				footer = typeahead_dataset.templates && typeahead_dataset.templates.footer;
			if (empty) {
				templates.empty = ['<div class="tt-empty">', empty, '</div>'].join('\n');
			}
			if (header) {
				templates.header = ['<div class="tt-header">', header, '</div>'].join('\n');
			}
			if (footer) {
				templates.footer = ['<div class="tt-footer">', footer, '</div>'].join('\n');
			}

			// Setup suggestion template for Typeahead:
			var _templates = typeahead_dataset.templates,
				_suggestion = _templates && _templates.suggestion;

			if (_suggestion) {
				if (all_suggestions[_suggestion] === undefined) {
					_suggestion = all_suggestions[_suggestion] = Handlebars.compile(_suggestion);
				} else {
					_suggestion = all_suggestions[_suggestion];
				}
				templates.suggestion = _suggestion;
			}

			var related = opts.related && opts.related.join(', ') || '',
				$related = $(related),

				bloodhound = $.extend({
					processQuery: function(query) {
						query = 'PARTIAL ' + query;
						$related.each(function(i) {
							var val = $(this).val();
							if (val) {
								if (query) {
									query += ' ';
								}
								query += ' PARTIAL ' + val;
							}
						});
						return query;
					}
				}, bloodhound_options),

				prefetch = opts.prefetch ? opts.prefetch : 0,
				remote = (opts.remote || opts.remote === undefined) ? true : false,
				key = opts.key || 'key',

				autocomplete = get_or_create_catalog(
					typeahead_dataset.name + ':' + related + ':' + key + ':' + prefetch + ':' + remote,
					typeahead_dataset.name,
					bloodhound,
					key,
					prefetch,
					remote),

				source = autocomplete.ttAdapter(),

				typeahead = {
					options: $.extend({
						// default Typeahead options:
						hint: true,
						highlight: true,
						minLength: 1
					}, typeahead_options),
					dataset: $.extend({
						// default Typeahead dataset:
						source: source,
						displayKey: 'key'
					}, typeahead_dataset, {
						templates: templates
					})
				};

			var tabaway,
				select,
				o = $.extend({
					key: 'key',
					alwaysSelect: false,
					selectOnTab: false,
					flash: true
				}, opts, {
					bloodhound: bloodhound,
					typeahead: typeahead
				}),

				// Create a hidden input that will hold the values
				id = $this.attr('id'),
				$hidden = $('<input type="hidden">')
					.val($this.val())
					.attr('name', $this.attr('name'))
					.attr('id', id + '_value'),

				autoFill = function(suggestion, silent) {
					var val = suggestion && suggestion[typeahead.dataset.displayKey];
					$this.val(val).typeahead('val', val).blur();//.trigger('change');

					for (var selector in o.autoFill) {
						var key = o.autoFill[selector],
							$elem = $(selector),
							old_val = $elem.val();
						val = suggestion && suggestion[key];
						if (val === undefined) {
							val = '';
						}
						if (old_val != val) {
							$elem.val(val).typeahead('val', val);
							if (!silent && o.flash) {
								var color = $elem.css('backgroundColor') || '#fff';
								$elem
									.animate({ backgroundColor: '#fe8' }, 20)
									.animate({ backgroundColor: color }, 2000, 'easeOutCirc');
							}
						}
					}
				},

				selected = function(event, suggestion, dataset, silent) {
					var focus = true;
					if (suggestion === null) {
						select = false;
						tabaway = false;
						return;
					}
					if (suggestion === undefined) {
						suggestion = {};
						focus = false;
					}
					if (event && event.type == 'typeahead:selected') {
						select = true;
						tabaway = true;
					}

					autoFillWrapper = (function(focus, select, tabaway) {
						runAutoFill = function() {
							autoFill(suggestion, silent);

							// The value has changed, so now we see if there are any
							// autoFill fields and set their value.
							$hidden.val(suggestion[o.key]).trigger('change');

							if (focus && tabaway) {
								// Also we focus the next input or the specified one in
								// options.focus.
								var $inputs, $selector, $input;
								if (select && o.focus) {
									$selector = $(o.focus);
								} else {
									$selector = $this.closest('form');
								}
								$inputs = $selector.find(
									'input:visible:not([disabled], [type=hidden]), select:visible:not([disabled]), textarea:visible:not([disabled]), button:visible:not([disabled])'
								);
								if ($inputs.length === 0) {
									$input = $selector;
								} else {
									var _input,
										_button,
										next_input = $inputs.index($this[0]);
									do {
										_input = $inputs.eq(++next_input);
										if (!$input) $input = _input;
										if (!(o.autoFill && o.autoFill['#' + _input.attr('id')])) {
											if (_input.hasClass('skip-auto-focus')) {
												continue;
											} else if (_input.length && _input[0].type == 'button') {
												if (!_button) _button = _input;
											} else if (!_input.val()) {
												$input = _input;
												break;
											}
										}
									} while(_input.length);
									if (!$input || $input.length === 0) {
										if (_button) {
											$input = _button;
										} else {
											$input = $inputs.first();
										}
									}
								}
								$input.focus();
							}
						};
						return runAutoFill;
					})(focus, select, tabaway);

					if (!(event && event.type == 'typeahead:selected')) {
						select = false;
						tabaway = false;
					}

					if (o.triggerOnSelected) {
						$this.trigger('autocomplete-selected', [suggestion, silent, autoFillWrapper]);
					} else {
						autoFillWrapper();
					}

				};

			// Apply typeahead
			$this
				.on('keydown.autocomple', function(e) {
					tabaway = false;
					select = false;
					if (e.keyCode === 9) {
						tabaway = true;
						select = o.selectOnTab;
					}
					if (o.alwaysSelect) {
						select = o.alwaysSelect;
					}
				})

				// Cleanup input (so duplicated inputs by typeahead are cleaner)
				.attr('id', o.id ? o.id : id + '_ac')
				.removeAttr('data-autocomplete')

				// Initialize Typeahead
				.typeahead(o.typeahead.options, o.typeahead.dataset)

				// Setup hidden input for values
				.after($hidden)
				.removeAttr('name')

				// recover input ID and disable browser's autocomplete
				.attr('id', id)
				.attr('autocomplete', 'off')

				// when something changes, do the stuff above (in selected)
				.on('typeahead:selected', selected)
				.on('typeahead:autocompleted', selected)
				.on('change.autocomple', function(e) {
					var val = $(this).val();
					$hidden.val(val).trigger('change');
					if (select && val) {
						// autocomplete first suggestion on TAB
						changing = true;
						source(val, function(suggestions) {
							selected(null, suggestions[0] || null, null, true);
						});
					}
				});
		});
	};
})(jQuery);
