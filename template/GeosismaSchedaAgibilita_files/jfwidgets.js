// See http://wiki.jqueryui.com/w/page/12138135/Widget%20factory
(function( $ ){
    // Master JSON field
    $.widget('ui.jsonfield', {
        options: {
            // True for debugging functions
            "debug_submit": false,
        },
        _create: function() {
            var self = this;

            // List of (check_function, trigger_function). Each time the
            // aggregate changes, check_function(dict) is run. If its return
            // value changed since the last check, trigger_function(dict) is
            // run.
            self.value_triggers = [];
            self.named_value_triggers = {};
            self.really_submit = true;
            self.modified = false;

            // Find ui components
            self.element.change(function(ev) {
                self.refresh(ev);
            });

            self.form = $(self.element[0].form);

            self.form.submit(function(ev) {
                var str = JSON.stringify(self._data);
                self.element.val(str);
                if (!self.really_submit)
                {
                    // Uncomment only for testing
                    console.log("Would submit", self._data, str)
                    ev.preventDefault();
                }
            });

            self.refresh();
        },

        _toggle_debug_submit: function(val) {
            var self = this;

            if (val)
            {
                // Add elements
                self.form.find("input[type=submit]").each(function(idx, el) {
                    var el = $(el);
                    var really = $("<input type='checkbox' checked>").change(function(el) {
                        self.really_submit = this.checked;
                    });
                    var span = $("<span class='debug_submit'>");
                    span.append(really);
                    span.append("really");
                    el.after(span);
                });
            }
            else
                // Remove elements
                self.element.find("input.debug_submit").detach();
        },

        data: function() {
            return this._data;
        },

        get: function(key) {
            return this._data[key];
        },

        set: function(key, val) {
            var self = this;

            // If nothing changes, we do nothing
            if (val == self._data[key])
                return;

            if (!self.modified)
            {
                self.modified = true;
                self._trigger("modified", null, {});
            }

            var named = self.named_value_triggers[key];

            // Get the value of all checkers before the change
            var pre = [];
            $.each(self.value_triggers, function(idx, el) { pre.push(el.check(self._data)); });
            var pre_named = [];
            if (named != undefined)
                $.each(named, function(idx, el) { pre_named.push(el.check(self._data[key])); });

            // Perform the change
            if (val == undefined)
                delete self._data[key];
            else
                self._data[key] = val;

            // Trigger for each checker that changed
            $.each(self.value_triggers, function(idx, el) {
                var post = el.check(self._data);
                if (post != pre[idx])
                    el.trigger(post, self._data);
            });
            if (named != undefined)
                $.each(named, function(idx, el) {
                    var post = el.check(self._data[key]);
                    if (post != pre_named[idx])
                        el.trigger(post, self._data);
                });
        },

        named_value_trigger: function(name, check, trigger) {
            // Store the trigger
            if (this.named_value_triggers[name] == undefined)
                this.named_value_triggers[name] = [];
            this.named_value_triggers[name].push({"check":check, "trigger":trigger});

            // Evaluate once
            trigger(check(this._data[name]), this._data);
        },

        value_trigger: function(check, trigger) {
            // Store the trigger
            this.value_triggers.push({"check":check, "trigger":trigger});

            // Evaluate once
            trigger(check(this._data), this._data);
        },

        disable_when_true: function(name, tag, elements) {
            if (arguments.length == 2)
            {
                elements = tag;
                tag = name;
            }
            var self = this;
            self.named_value_trigger(name, function (val) { return val ? true : false }, function(val, data) {
                $.each(elements, function(idx, el) {
                    $(el).data("poly_subfield").disable(tag, val);
                });
            });
        },

        disable_when_false: function(name, tag, elements) {
            if (arguments.length == 2)
            {
                elements = tag;
                tag = name;
            }
            var self = this;
            self.named_value_trigger(name, function (val) { return val ? false : true }, function(val, data) {
                $.each(elements, function(idx, el) {
                    $(el).data("poly_subfield").disable(tag, val);
                });
            });
        },

        refresh: function(ev) {
            var self = this;
            var str = self.element.val();
            var data = $.parseJSON(str);
            // If the value contains rubbish, reset to the empty object
            if (typeof(data) != "object" || $.isArray(data))
                data = {};
            self._data = data;
            //self._trigger("changed", ev);
        },

        _setOption: function(key, value) {
            switch (key) {
                case "data":
                    this.refresh();
                    break;
                case "debug_submit":
                    this._toggle_debug_submit(value);
                    break;
            }
            $.Widget.prototype._setOption.apply(this, arguments);
        },
    });

    // Slave fields
    $.widget('ui.subfield', {
        options: {
            // Master field which contains the JSON data
            master: null,
        },

        _create: function() {
            var self = this;

            // polymorphically, without having to worry about their type
            self.widgetEventPrefix = "subfield";

            // Force a common event prefix, so we can bind all subfields
            // Add a pointer for home-made polimorphism
            self.element.data("poly_subfield", self);

            // Field name (fallback to ID if not a form field)
            self.name = self.element.attr("name");
            if (!self.name)
                self.name = self.element.attr("id");

            if (self.options.master == null)
            {
                var master_id = self.element.attr("master");
                if (master_id)
                    self.options.master = $("#" + master_id);
            }

            if (self.options.master)
            {
                // Hook into master
                self.master = self.options.master.data("jsonfield");
                self.options.master.change(function(ev) {
                    self.refresh();
                });
            } else
                self.master = null;

            // Disabled status
            self.disabled = false;
            // Set of widgets that want us disabled
            self.disabled_masters = {};
            // Saved value we had at the time we disabled
            self.last_value = null;
        },

        get: function() {
            var self = this;
            if (!self.master)
                return undefined;
            return self.master.get(self.name);
        },

        set: function(val) {
            var self = this;
            if (self.master)
                self.master.set(self.name, val);
            self._value_to_field(val);
            self._trigger("change", null, { "name": self.name, "val": val });
        },

        refresh: function() {
            var self = this;
            self.set(self.get());
        },

        disable: function(name, val) {
            var self = this;

            if (val)
                self.disabled_masters[name] = true;
            else
                delete self.disabled_masters[name];

            var should_be_disabled = false;
            $.each(self.disabled_masters, function(key, val) {
                should_be_disabled = true;
            });

            if (should_be_disabled && !self.disabled)
            {
                self.last_value = self.get();
                self.disabled = true;
                self._disable_field(true);
                self.set(undefined);
            } else if (!should_be_disabled && self.disabled) {
                self.set(self.last_value);
                self.disabled = false;
                self._disable_field(false);
            }
        },

        // Set the field value
        _value_to_field: function(val) {},

        // Enable/disable a field if val is false/true
        _disable_field: function(val) {},
    });

    $.widget('ui.subfield_formelement', $.ui.subfield, {
        _create: function() {
            var self = this;

            $.ui.subfield.prototype._create.call(self);

            self.disable_onchange = false;
            self.element.change(function(ev) {
                if (self.disable_onchange)
                    return;
                self._on_change(ev);
            });

            self.refresh();
        },

        _on_change: function(ev) {
            var self = this;
            if (self.disable_onchange) return;

            var oldval = self.get();
            var newval = self._value_from_field();

            // Update the master dict when the value changes
            if (oldval != newval)
                self.set(newval);
        },

        _value_from_field: function() {
            var self = this;
            var fval = self.element.val();
            var res = self._validate(fval);
            if (res != fval)
                self._value_to_field(res);
            return res;
        },

        _value_to_field: function(val) {
            var self = this;
            if (self.element.val() != val)
            {
                self.disable_onchange = true;
                self.element.val(val);
                self.disable_onchange = false;
            }
        },

        // Validate a value, returning the value or undefined if it fails to validate
        _validate: function(val) { return val; },

        _disable_field: function(val) {
            var self = this;
            self.element[0].disabled = val;
        },
    });

    $.widget('ui.subfield_text', $.ui.subfield_formelement, {});

    $.widget('ui.subfield_int', $.ui.subfield_formelement, {
        _validate: function(val) {
            var res = parseInt(val, 10);
            if (isNaN(res))
                return undefined;
            return res;
        },
    });

    $.widget('ui.subfield_float', $.ui.subfield_formelement, {
        _validate: function(val) {
            var res = parseFloat(val, 10);
            if (isNaN(res))
                return undefined;
            return res;
        },
    });

    $.widget('ui.subfield_radio', $.ui.subfield_formelement, {
        _create: function() {
            var self = this;

            $.ui.subfield_formelement.prototype._create.call(self);

            self.siblings = $("input[type=radio][name=" + self.name + "]");

            // Make radio buttons unselectable
            self.element.mouseup(function() { this.waschecked = this.checked })
            self.element.click(function() {
                if (this.waschecked && this.checked)
                {
                    this.checked = false
                    self.set(null);
                }
            })
        },

        _value_from_field: function() {
            var self = this;

            // Do not return the value of this field, but the value of the
            // currently selected field, or 'undefined' if none is selected
            var form = self.element[0].form;
            var name = self.element.attr("name");
            var fields = self.element[0].form[name];
            var val = undefined;
            $.each(fields, function(idx, el) {
                if (el.checked)
                    val = el.value;
            });

            return val;
        },

        _value_to_field: function(val) {
            var self = this;
            self.disable_onchange = true;

            // Set the status of all radio buttons
            var form = self.element[0].form;
            var name = self.element.attr("name");
            var fields = self.element[0].form[name];
            $.each(fields, function(idx, el) {
                el.checked = (val == el.value);
            });
            self.disable_onchange = false;
        },

        _disable_slave: function(lv, name, val) {
            var self = this;
            var el = self.element[0];

            if (val)
            {
                self.disabled_masters[name] = true;
                self.last_value = lv;
            } else {
                delete self.disabled_masters[name];
                el.checked = (lv == el.value);
            }

            self.disabled = val;
            self._disable_field(val);
        },

        disable: function(name, val) {
            // The first field that gets disabled takes care of disabling all
            // others via _disable_slave. Everything else is idempotent, so
            // disabling/enabling the other fields does nothing.
            var self = this;

            if (val)
                self.disabled_masters[name] = true;
            else
                delete self.disabled_masters[name];

            var should_be_disabled = false;
            $.each(self.disabled_masters, function(key, val) {
                should_be_disabled = true;
            });

            if (should_be_disabled && !self.disabled)
            {
                var lv = self.get();
                // Disable this and all other siblings
                $.each(self.siblings, function(idx, ev) { $(ev).data("poly_subfield")._disable_slave(lv, name, true); });
                self.set(undefined);
            } else if (!should_be_disabled && self.disabled) {
                $.each(self.siblings, function(idx, ev) { $(ev).data("poly_subfield")._disable_slave(lv, name, false); });
                self.set(self.last_value);
            }
        },
    });

    $.widget('ui.subfield_checkbox', $.ui.subfield_formelement, {
        _value_from_field: function() {
            var self = this;

            var val = self.element.prop("checked");
            if (!val) val = null;

            return val;
        },

        _value_to_field: function(val) {
            self.disable_onchange = true;
            this.element.prop("checked", val ? true : false);
            self.disable_onchange = false;
        },

        uncheck: function() {
            var self = this;
            self.element.prop("checked", false);
            self.set(null);
        },
    });

    // Abstract base for fields with repeated multiline contents
    $.widget('ui.subfield_multiline', $.ui.subfield, {
        _create: function() {
            var self = this;

            $.ui.subfield.prototype._create.call(self);

            self.rows = self.element.find(".subfield_multiline_rows");

            self.disable_onchange = false;
            self.rows.change(function(ev) {
                if (self.disable_onchange)
                    return;
                self._on_change(ev);
            });
        },

        // Append a new row. el is the initial data for the new row
        add_field: function(initial) {
            var self = this;
            self._add_field(initial);
            self._on_change();
        },

        // Render the widget used to delete a row
        _render_delete_row_widget: function(el) {
            // please reimplement with a nicer delete button
            var self = this;
            var res = $("<a href='#'>[X]</a>");
            res.click(function(ev) {
                self._delete_rows($(ev.target));
                ev.preventDefault();
            });
            return res;
        },

        // Delete the row(s) that contains the given jquery element(s)
        _delete_rows: function(row_element) {
            var self = this;
            row_element.closest(".managed").detach();
            self.set(self._value_from_field())
        },

        _on_change: function(ev) {
            var self = this;
            if (self.disable_onchange) return;

            var oldval = self.get();
            var newval = self._value_from_field();

            // Update the master dict when the value changes
            if (oldval != newval)
                self.set(newval);
        },

        // If the existing row can be set to val, do it and return true. Else
        // return false.
        _update_row: function(row, val) {
            // Please implement it in child widgets, to reuse existing DOM
            // elements instead of recreating the whole managed list at every
            // value change: this avoids flickers and preserves tab navigation.
            return false;
        },

        // Set the field value
        _value_to_field: function(val) {
            var self = this;

            self.disable_onchange = true;

            if (val == undefined)
                val = self.options.default_when_blank;

            // Get the existing widgets
            var old = self.rows.find(".managed");

            // Preserve the leading elements, if they can be updated
            var lead = old.length < val.length ? old.length : val.length;
            var i = 0;
            for (; i < lead; ++i)
                if (!self._update_row($(old[i]), val[i]))
                    break;

            var first_unchanged = i;

            // Remove the remaining widgets
            for (var i = first_unchanged; i < old.length; ++i)
                $(old[i]).detach();

            // Append all new fields
            for (var i = first_unchanged; i < val.length; ++i)
                self._add_field(val[i]);

            self.disable_onchange = false;
        },
    });

    $(function() {
        // Initialize all JSONInput fields looking them up by class
        $("input.JSONInput").jsonfield();
    });
})( jQuery );
