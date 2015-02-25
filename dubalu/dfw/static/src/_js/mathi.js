/**
 * jQuery Math Inputs plugin v1.0
 * @author German M. Bravo (Kronuz) [german DOT mb AT deipi DOT com]
 * @requires jQuery
 *
 * Copyright (c) 2014, deipi.com LLC
 * All rights reserved.
 *
 * Date: 2014-04-10
 * Last update: 2014-12-05
 */
(function($) {
	if ($.fn._mathi_val === undefined) {
		$.fn._mathi_val = $.fn.val;
	}

	function mathi_capture() {
		var $this = $(this),
			data = $this.data('mathi');
		if (data === undefined) {
			data = {};
			$this.data('mathi', data);
		}
		if ($this.attr('type') !== 'text' || data.raw === undefined) {
			$this.attr('type', 'text');
			data.value = $this._mathi_val();
			if (data.raw === undefined) {
				data.raw = data.value;
			} else {
				$this._mathi_val(data.raw);
			}
		}
	}

	function mathi_calculate() {
		var $this = $(this),
			data = $this.data('mathi'),
			math = $this.attr('math');

		if ($this.attr('type') !== 'text' || data === undefined) {
			return data;
		}

		mathi_capture.call(this);

		var raw = $this._mathi_val();  // get the current value

		if (data.raw === raw) {
			return data;
		}

		var calculated = raw,
			_sanitized = raw.replace(/[^0-9\+\-\*\/\%\(\)\.]+/, ''), // sanitize, so a smarty-pants can't do bad stuff
			sanitized = [];

		_sanitized = _sanitized.replace(/\+([0-9.]+)%/, '*(1+($1/100))');
		_sanitized = _sanitized.replace(/-([0-9.]+)%/, '*(1-$1/100)');

		var prev_c_is_digit = false;

		// a zero starting number is interpreted as octal by javascript
		// this is weird for accounting purposes; hex numbers are not a problem
		for (var i = 0; i < _sanitized.length; ++i) {
			var c = _sanitized[i];
			if (c == '0' && !prev_c_is_digit) {
				continue;
			}
			sanitized.push(c);
			prev_c_is_digit = c == '.' || ('0' <= c && c <= '9');
		}
		sanitized = sanitized.join("");

		if (sanitized) {
			try {
				calculated = eval(sanitized);   // jshint ignore:line
				calculated = calculated.toFixed(math == 'integer' ? 0 : 2);
			} catch (error) {}
		}

		data.raw = raw;
		data.value = calculated;
		return data;
	}

	$.fn.val = function(value) {
		var current_value;
		if (this.length === 1) {
			var data = mathi_calculate.call(this);
			if (data && data.value !== undefined) {
				current_value = data.value;
			} else {
				current_value = this._mathi_val();
			}
		} else {
			current_value = this._mathi_val();
		}
		if (value === undefined) {
			return current_value;
		} else {
			var _current_value = parseFloat(current_value),
				_value = parseFloat(value);
			if (_current_value !== _value || (isNaN(current_value) || isNaN(value)) && current_value !== value) {
				$(this).removeData('mathi');
				return this._mathi_val(value);
			}
			return this;
		}
	};

	$.fn.mathi = function(namespaces, fn, run) {
		this
			.on('focus.mathi', mathi_capture)
			.on('keypress.mathi', mathi_capture)
			.on('change.mathi', mathi_calculate)
			.on('blur.mathi', function(e) {
				mathi_capture.call(this);
				var $this = $(this),
					data = $this.data('mathi');
				$this
					.attr('type', 'number')
					._mathi_val(data.value)  // set the value
					.trigger('change');
			});
	};

})(jQuery);
