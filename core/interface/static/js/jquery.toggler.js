/* https://www.jqueryscript.net/form/Sliding-Switch-jQuery-simpleToggler.html */

;(function ( $, window, document, undefined ) {


    let pluginName = "checkToggler",
        defaults = {
            labelOn: "On",
            labelOff: "Off"
        };

    // The actual plugin constructor
    function CheckToggler ( element, options ) {
        this.element = element;

        this.settings = $.extend( {}, defaults, options );
        this._defaults = defaults;
        this._name = pluginName;

        this._template = '<div class="ui-stoggle on"><div class="ui-stoggle--inner"><span class="ui-stoggle--label-on"><i class="ui-stoggle--label-text">On</i></span><span class="ui-stoggle--label-off"><i class="ui-stoggle--label-text">Off</i></span></div><span class="ui-stoggle--slider"><i></i></span></div>';

        this.init();
    }

    CheckToggler.prototype = {
        init: function () {
            this.$element = $(this.element);

            this.$element.addClass('ui-stoggle--hidden');

            this.$uiToggle = $(this._template).insertAfter(this.$element);
            this.$uiToggleLabelOnText = $('.ui-stoggle--label-on .ui-stoggle--label-text', this.$uiToggle).text(this.settings.labelOn);
            this.$uiToggleLabelOffText = $('.ui-stoggle--label-off .ui-stoggle--label-text', this.$uiToggle).text(this.settings.labelOff);

            this.$element.on('change', $.proxy( this.onChange, this ));

            this.$uiToggle.on('click', $.proxy( this.onUIClick, this ));

            this.applyOptions();
            this.onChange(null);

        },

        applyOptions: function(){

        },

        onUIClick: function (e) {
            this.$element.trigger('click');
            console.log('UI Click: ' + this.$element.prop('checked'));
        },

        onChange: function (e) {
            if (this.$element.prop('checked')) {
                this.$uiToggle.addClass('on').removeClass('off');
            }
            else {
                this.$uiToggle.addClass('off').removeClass('on');
            }
        }
    };

    // A really lightweight plugin wrapper around the constructor,
    // preventing against multiple instantiations
    $.fn[ pluginName ] = function ( options ) {
        return this.each(function() {
            if ( !$.data( this, "plugin_" + pluginName ) ) {
                $.data( this, "plugin_" + pluginName, new CheckToggler( this, options ) );
            }
        });
    };

})( jQuery, window, document );
