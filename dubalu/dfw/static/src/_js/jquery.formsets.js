/**
 * jQuery Formset 1.2
 * @author Stanislaus Madueke (stan DOT madueke AT gmail DOT com)
 * @requires jQuery 1.2.6 or later
 *
 * Copyright (c) 2009, Stanislaus Madueke
 * All rights reserved.
 *
 * Licensed under the New BSD License
 * See: http://www.opensource.org/licenses/bsd-license.php
 */

(function($) {
	'use strict';

	var FormSet = function(element, options) {
		this.$element = $(element);
		var related = this.$element.attr('related'),
			$formset = related ? $('#' + related) : this.$element;

		if (!$formset.hasClass('dynamic-formset')) {
			this.$formset = $formset.closest('.dynamic_formset');
		} else {
			this.$formset = $formset;
		}

		this.options = $.extend(
			{},
			options,
			this.$formset.data('dynamic-formset') || {}
		);
		this.$container = this.$formset.find('> div.form-form') || $('#' + this.$formset.attr('related'));
		if (!this.$container.attr('prefix')) {
			// Ensure there is a prefix for "name"
			throw new Error("FormSet must have a container with prefix!");
		}
		// The following is the DIV prefix (for DOM manipulation)
		var prefix = this.$container.attr('id').replace('div_id_', '');
		this.initialForms = parseInt($('#id_' + prefix + '-INITIAL_FORMS').val(), 10);
		this.minNumForms = parseInt($('#id_' + prefix + '-MIN_NUM_FORMS').val(), 10);
		this.maxNumForms = parseInt($('#id_' + prefix + '-MAX_NUM_FORMS').val(), 10);
		this.$totalForms = $('#id_' + prefix + '-TOTAL_FORMS');
		this.formSeq = parseInt(this.$totalForms.val(), 10);
		this.$loader = $('#' + this.options.loaderId);

		var $forms = this.$container.find('> .subform > .dynamic_formset_form');
		if (this.initialForms) {
			$forms.each(function(curForm) {
				if (curForm < this.initialForms) {
					var $del = this.$formset.closestDescendant('a.delete-row');
					if ($del.hasClass('disable-delete')) {
						$del.siblings('input:hidden[name $= "-DELETE"]').remove();
						$del.remove();
					}
				}
			});
		}
		this.updateForms($forms, this.$loader);
	};

	FormSet.prototype.updateForms = function($forms, $loader) {
		// Filter only visible forms.
		var $visible_forms = $forms.filter(':visible');

		// If the formset is initialized with a single form, hide the delete button.
		var $first_delete = $visible_forms.closestDescendant('a.delete-row');
		if ($visible_forms.length <= this.minNumForms) {
			$first_delete.hide();
		} else {
			$first_delete.show();
		}

		// It the number of forms is equal or greater than the maximum number of allowed forms, hide the loader.
		if ($visible_forms.length >= this.maxNumForms) {
			$loader.hide();
		} else {
			$loader.show();
		}
	};

	FormSet.prototype.elementIndexUpdater = function(prefix) {
		// This method updates an element's name and prefix attributes with a given index number.
		var idRegex = new RegExp('(' + prefix + '-\\d+-)'),
			update = function(elem, attr, replacement) {
				var val = elem.attr(attr);
				if (val !== undefined) {
					var newval = val.replace(idRegex, replacement);
					if (newval !== val) {
						elem.attr(attr, newval);
					}
				}
			};
		return function(idx) {
			var replacement = prefix + '-' + idx + '-';
			return function() {
				var elem = $(this);
				update(elem, 'name', replacement);
				update(elem, 'prefix', replacement);
			};
		};
	};

	FormSet.prototype.deleteForm = function(element, callback) {
		var self = this,
			$element = $(element),
			$formset = this.$formset,
			$container = this.$container,
			initialForms = this.initialForms,
			$forms = $container.find('> .subform > .dynamic_formset_form'),
			curForm = $forms.index(this.$form),
			$loader = this.$loader,
			$totalForms = this.$totalForms,
			prefix = $container.attr('prefix'),
			formCount = parseInt(this.$totalForms.val(), 10),
			$form = $element.closest('.dynamic_formset_form'),
			$del;

		if (curForm !== -1 && curForm < initialForms) {
			$del = $form.closestDescendant('input:hidden[name $= "-DELETE"]');
		}

		$forms = $forms.not($form);
		if ($del && $del.length) {
			// We're dealing with a form which is part of an initial form;
			// rather than remove this form from the DOM, we'll mark it as
			// deleted and hide it, then let Django handle the deleting.
			$del.val('on');
			$form.hide();
		} else {
			$form.remove();

			// Update the TOTAL_FORMS form count.
			if ($forms.length !== formCount - 1) {
				console.error("FormSet.deleteForm: Form count mismatch: " + $forms.length + " !== " + (formCount - 1), ' (#' + $totalForms.attr('id') + ')');
			}
			$totalForms.val($forms.length);

			// Also update names and IDs for all remaining form controls so they remain in sequence:
			var updateElementIndex = self.elementIndexUpdater(prefix);
			$forms.each(function(i) {
				$(this).find('[name], [prefix]').add(this).each(updateElementIndex(i));
			});
		}

		this.updateForms($forms, $loader);

		if (typeof callback === 'function') {
			callback.apply(self, [$form, $element]);
		}

		// trigger event which can be catched externally
		$formset.trigger('formset-deleted', [$form, $formset]);
	};

	FormSet.prototype.addForm = function(element, callback) {
		var self = this,
			$element = $(element),
			$formset = this.$formset,
			$container = this.$container,
			$totalForms = this.$totalForms,
			prefix = $container.attr('prefix'),
			$forms;

		$.ajax({
			url: $element.attr('src'),
			async: !callback,
			success: function(data) {
				var formCount = parseInt($totalForms.val(), 10),
					$form = $(data.replace(/__fp__/g, prefix.replace(/-[^-]*$/, '')).replace(/__fc__/g, self.formSeq));
				self.formSeq += 1;
				$container.find('> .subform').append($form);

				$forms = $container.find('> .subform > .dynamic_formset_form');

				// Update the TOTAL_FORMS form count.
				if ($forms.length !== formCount + 1) {
					console.error("FormSet.addForm: Form count mismatch: " + $forms.length + " !== " + (formCount + 1), ' (#' + $totalForms.attr('id') + ')');
				}
				$totalForms.val($forms.length);

				// Also update names and IDs for all remaining form controls so they remain in sequence:
				var updateElementIndex = self.elementIndexUpdater(prefix);
				$forms.each(function(i) {
					$(this).find('[name], [prefix]').add(this).each(updateElementIndex(i));
				});

				self.updateForms($forms, $element);

				if (typeof callback === 'function') {
					callback.apply(self, [$form, $element]);
				}

				$form.liveSetup();

				// trigger event which can be catched externally.
				$formset.trigger('formset-added', [$form, $element]);
			}
		});
	};

	$.fn.formset = function(option, callback) {
		return this.each(function () {
			var $this = $(this),
				related = $this.attr('related'),
				$related = related ? $('#' + related) : $this,  // Try to get dynformset object from related container
				data = $related.data('dynformset') || $this.data('dynformset'),
				options = typeof option == 'object' && option;

			if (!data) {
				data = new FormSet(this, options);
				$related.data('dynformset', data);
				$this.data('dynformset', data);
			}

			if (option == 'add') data.addForm(this, callback);
			else if (option == 'delete') data.deleteForm(this, callback);
		});
	};

	$(document).on('click', '.dynamic_formset a.delete-row', function(e) {
		$(this).formset('delete');
	});

	$(document).on('click', 'a.add-row', function(e) {
		$(this).formset('add');
	});

})(jQuery);
