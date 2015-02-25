/* ----------------------------------------------------------------------------
// Ezdz [izy-dizy]
// Licensed under the MIT license.
// http://github.com/jaysalvat/ezdz/
// ----------------------------------------------------------------------------
// Copyright (C) 2013 Jay Salvat
// http://jaysalvat.com/
// --------------------------------------------------------------------------*/
(function ($) {
    $.validators = function(options) {
        var defaults = {
            validators: {},
            onValidated: function() {}
        };

        function _resolveValidator(name) {
            var validator = this.validators[name];
            if (validator) {
                if ($.isFunction(validator)) {
                    return validator;
                }
                if ($.isFunction($.validators.prototype[validator])) {
                    return $.validators.prototype[validator];
                }
            }
            return validator;
        }

        function _check() {
            for (var name in this.validators) {
                var validator = _resolveValidator.call(this, name);
                if (validator === undefined || $.isFunction(validator)) {
                    return;  // validations still running!
                }
            }
            for(var error in this.errors) {
                if (this.errors.hasOwnProperty(error)) {
                    if (this.errors[error]) {
                        this.has_errors = true;
                        break;
                    }
                }
            }
            for (var i in this.callbacks) {
                var onValidated = this.callbacks[i];
                if ($.isFunction(onValidated)) {
                    if (onValidated.apply(this, arguments) === false) {
                        break;
                    }
                }
            }
        }

        return $.extend(defaults, options, {
            callbacks: null,

            valid: true,
            warning: false,
            has_errors: null,
            errors: {},

            validated: function(name, valid) {
                // sets the validator status (particularly for delayed validations)
                if (typeof(valid) !== 'boolean' && valid !== null) {
                    valid = false;
                    console.error("validated() for " + name + " should be called with a true, false or null as the second parameter!");
                }
                if (valid === false || valid === null) {
                    this.valid = valid;
                }
                this.validators[name] = valid;
                _check.apply(this, this.args);
            },

            validate: function() {
                this.args = arguments;
                this.callbacks = [];
                this.callbacks.push(this.onValidated);
                for (var name in this.validators) {
                    var validator = _resolveValidator.call(this, name);
                    var onValidated = validator.onValidated;
                    if (onValidated) {
                        this.callbacks.push(onValidated);
                    }
                    if ($.isFunction(validator)) {
                        // validators should return true, false or null if they are done
                        // validating or undefined if they're working on the
                        // validation and at a later time set validators[validator]
                        // to true/false/null themselves.
                        var valid = validator.apply(this, arguments);
                        if (valid === false || valid === null) {
                            this.valid = valid;
                        }
                        this.validators[name] = valid;
                    }
                }
                _check.apply(this, this.args);
                return this;
            }
        });
    };
})(jQuery);

(function ($) {
    // Default settings
    var defaults = {
        className:     '',
        text:          'Drop a file',
        previewImage:  true,
        value:         null,
        classes: {
            main:      'ezdz-dropzone',
            enter:     'ezdz-enter',
            reject:    'ezdz-reject',
            accept:    'ezdz-accept',
            warning:   'ezdz-warning',
            focus:     'ezdz-focus'
        },
        html: {
            accept:    '<i class="fa fa-check"></i>',
            warning:   '<i class="fa fa-clock-o"></i>',
            reject:    '<i class="fa fa-times"></i>'
        },
        validators: {
            maxSize:   null,
            width:     null,
            maxWidth:  null,
            minWidth:  null,
            height:    null,
            maxHeight: null,
            minHeight: null
        },
        init:   function() {},
        enter:  function() {},
        leave:  function() {},
        reject: function() {},
        accept: function() {},
        format: function(filename) {
            return filename;
        }
    };

    // Main plugin
    $.ezdz = function(element, options) {
        this.settings = $.extend(true, {}, defaults, $.ezdz.defaults, options);
        this.$input   = $(element);

        var self      = this,
            settings  = self.settings,
            $input    = self.$input;

        if (!$input.is('input[type="file"]')) {
            return;
        }

        // Stop if not compatible with HTML5 file API
        if (!$.ezdz.isBrowserCompatible()) {
            return;
        }

        // private: Init the plugin
        var init = function() {
            var $ezdz, $container, value;

            $container = $input.closest('.' + settings.classes.main.replace(/ /g, '.'));

            if (!$container.length) {
                // Build the container
                $container = $('<div class="' + settings.classes.main + '" />');

                // Build the whole dropzone
                $input
                    .wrap($container)
                    .before('<div>' + settings.text + '</div>');
            }

            $container

            .on('dragover.ezdz', function() {
                $(this).addClass(settings.classes.enter);

                if ($.isFunction(settings.enter)) {
                     settings.enter.apply(this);
                }
            })

            .on('dragleave.ezdz', function() {
                $(this).removeClass(settings.classes.enter);

                if ($.isFunction(settings.leaved)) {
                    settings.leaved.apply(this);
                }
            })

            .addClass(settings.className);

            $ezdz = $input.parent('.' + settings.classes.main.split(' ').join('.'));

            // Preview a file at start if it's defined
            value = settings.value || $input.data('value');

            if (value) {
                self.preview(value);
            }

            // Trigger the init callback
            if ($.isFunction(settings.init)) {
                 settings.init.apply($input, [ value ]);
            }

            // Events on the input
            $input

            .on('focus.ezdz', function() {
                $ezdz.addClass(settings.classes.focus);
            })

            .on('blur.ezdz', function() {
                $ezdz.removeClass(settings.classes.focus);
            })

            .on('change.ezdz', function() {
                var file = this.files[0];

                // No file, so user has cancelled
                if (!file) {
                    return;
                }

                // Info about the dropped or selected file
                var basename  = file.name.replace(/\\/g,'/').replace( /.*\//, ''),
                    extension = file.name.split('.').pop(),
                    formatted = settings.format(basename);

                file.extension = extension;

                var validateSize = function(element, file) {
                    valid = true;

                    // Validator
                    if (settings.validators.maxSize && file.size > settings.validators.maxSize) {
                        valid = false;
                        this.errors.maxSize = true;
                    }

                    return valid;
                };

                var validateAccept = function(element, file) {
                    // Mime-Types
                    var allowed  = $(element).attr('accept'),
                        accepted = false;

                    // Check the accepted Mime-Types from the input file
                    if (allowed) {
                        var types = allowed.split(/[,|]/);

                        for (var i in types) {
                            var type = $.trim(types[i]);

                            if (type.indexOf('*.') === 0) {
                                type = type.replace('*.', '.');
                            }
                            if (type[0] == '.') {
                                if (type ==  '.' + file.extension) {
                                    accepted = true;
                                    break;
                                }
                            }

                            if (file.type == type) {
                                accepted = true;
                                break;
                            }

                            // Mime-Type with wildcards ex. image/*
                            if (type.indexOf('/*') !== -1) {
                                var a = type.replace('/*', ''),
                                    b = file.type.replace(/(\/.*)$/g, '');

                                if (a == b) {
                                    accepted = true;
                                    break;
                                }
                            }
                        }

                        if (!accepted) {
                            this.errors.mimeType = true;
                        }
                    } else {
                        accepted = true;
                    }

                    return accepted;
                };

                var validateImage = function(element, file) {
                    var that = this,
                        loaded = false;

                    if (file.data.indexOf('data:image/') !== 0) {
                        return true;
                    }

                    this.img = new Image();
                    this.img.src = file.data;

                    var onload = function() {
                        if (loaded) return;
                        loaded = true;

                        var valid = true,
                            isImage = (that.img.width && that.img.height);

                        if (isImage) {
                            file.width  = that.img.width;
                            file.height = that.img.height;

                            if (settings.validators.width && that.img.width != settings.validators.width) {
                                that.errors.width = true;
                                valid = false;
                            }

                            if (settings.validators.maxWidth && that.img.width > settings.validators.maxWidth) {
                                that.errors.maxWidth = true;
                                valid = false;
                            }

                            if (settings.validators.minWidth && that.img.width < settings.validators.minWidth) {
                                that.errors.minWidth = true;
                                valid = false;
                            }

                            if (settings.validators.height && that.img.height != settings.validators.height) {
                                that.errors.height = true;
                                valid = false;
                            }

                            if (settings.validators.maxHeight && that.img.height > settings.validators.maxHeight) {
                                that.errors.maxHeight = true;
                                valid = false;
                            }

                            if (settings.validators.minHeight && that.img.height < settings.validators.minHeight) {
                                that.errors.minHeight = true;
                                valid = false;
                            }

                            if (!valid) {
                                delete that.img;
                            }
                        } else {
                            delete that.img;
                        }
                        that.validated('validateImage', valid);
                    };

                    this.img.onload = onload;
                    setTimeout(onload, 0);
                };

                var onValidated = function(element, file) {
                    // Reset the accepted / rejected classes
                    $ezdz.removeClass(settings.classes.reject + ' ' + settings.classes.accept + ' ' + settings.classes.warning);

                    // The file is validated, so added to input
                    if (this.valid) {
                        var classes, html, funct;
                        if (this.warning) {
                            classes = settings.classes.warning;
                            html = settings.html.warning;
                            if ($.isFunction(settings.warning)) {
                                funct = settings.warning;
                            } else if ($.isFunction(settings.accept)) {
                                funct = settings.accept;
                            }
                        } else {
                            classes = settings.classes.accept;
                            html = settings.html.accept;
                            if ($.isFunction(settings.accept)) {
                                funct = settings.accept;
                            }
                        }

                        $ezdz.find('img').remove();

                        if (settings.previewImage && this.img) {
                            $ezdz.find('> div:first').html($(this.img).fadeIn());
                        } else {
                            $ezdz.attr('title', formatted);
                            $ezdz.find('> div:first').html(html);
                        }

                        $ezdz.addClass(classes);

                        // Trigger the accept callback
                        if (funct) {
                             funct.apply(element, [file]);
                        }
                    // The file is invalidated, so rejected
                    } else {
                        if (this.valid === false) $(element).val('');

                        $ezdz.find('> div:first').html(settings.html.reject);

                        $ezdz.addClass(settings.classes.reject);

                        // Trigger the reject callback
                        if ($.isFunction(settings.reject)) {
                             settings.reject.apply(element, [file, this.errors]);
                        }
                    }
                };

                // Read the added file
                var reader = new FileReader(file);

                reader.readAsDataURL(file);

                reader.onload = reader.onerror = function(e) {
                    file.data = e.target && e.target.result;
                    var validator = $.validators({
                        onValidated: onValidated,
                        validators: {
                            validateSize: validateSize,
                            validateAccept: validateAccept,
                            validateImage: validateImage
                        }
                    });
                    var vals = $input.data('validators');
                    vals = vals && vals.split(' ');
                    for (var i in vals) {
                        var v = vals[i];
                        if ($.validators.prototype[v]) {
                            validator.validators[v] = v;
                        } else {
                            console.error('Invalid validator name: ' + v);
                        }
                    }
                    validator.validate(element, file);
                };

            });
        };

        init();
    };

    // Inject a file or image in the preview
    $.ezdz.prototype.preview = function(path, callback) {
        var settings  = this.settings,
            $input    = this.$input,
            $ezdz     = $input.parent('.' + settings.classes.main),
            basename  = path.replace(/\\/g,'/').replace( /.*\//, ''),
            formatted = settings.format(basename);

        var img = new Image();
        img.src = path;

        // Is an image
        img.onload = function() {
            $input.closest('.ezdz-dropzone').find('div').html($(img).fadeIn());

            if ($.isFunction(callback)) {
                 callback.apply(this);
            }
        };

        // Is not an image
        img.onerror = function() {
            $ezdz.find('div').html('<span>' + formatted + '</span>');

            if ($.isFunction(callback)) {
                 callback.apply(this);
            }
        };

        $ezdz.addClass(settings.classes.accept);
    };

    // Destroy ezdz
    $.ezdz.prototype.destroy = function() {
        var settings = this.settings,
            $input   = this.$input;

        $input.parent('.' + settings.classes.main).replaceWith($input);
        $input.off('*.ezdz');
        $input.data('ezdz', '');
    };

    // Extend settings
    $.ezdz.prototype.options = function(options) {
        var settings = this.settings;

        if (!options) {
            return settings;
        }

        $.extend(true, this.settings, options);
    };

    // Get input container
    $.ezdz.prototype.container = function() {
        var settings = this.settings,
            $input   = this.$input;

        return $input.parent('.' + settings.classes.main);
    };

    // Is browser compatible
    $.ezdz.isBrowserCompatible = function() {
        return !!(window.File && window.FileList && window.FileReader);
    };

    // Default options
    $.ezdz.defaults = defaults;

    // jQuery plugin
    $.fn.ezdz = function(options) {
        var args = arguments,
            plugin = $(this).data('ezdz');

        if (!plugin) {
            return $(this).data('ezdz', new $.ezdz(this, options));
        }
        if (typeof options == 'string') {
            if (plugin[options]) {
                return plugin[options].apply(plugin, Array.prototype.slice.call(args, 1));
            } else {
                $.error('Ezdz error - Method ' +  options + ' does not exist.');
            }
        }
    };
})(jQuery);
