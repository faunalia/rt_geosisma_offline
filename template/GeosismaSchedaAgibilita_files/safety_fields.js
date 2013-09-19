// See http://wiki.jqueryui.com/w/page/12138135/Widget%20factory
(function( $ ){
    // Master JSON field
    $.widget('ui.subfield_observations', $.ui.subfield_multiline, {
        options: {
            // Default value to use when the value would have no fields
            default_when_blank: [
                ["", ""],
            ],
        },

        _create: function() {
            var self = this;

            $.ui.subfield_multiline.prototype._create.call(self);

            self.element.find(".observationsfield_actions_add").click(function(ev) {
                self.add_field(["", ""]);
                ev.preventDefault();
            });

            self.refresh();
        },

        // Render the widget used to delete a row
        _render_delete_row_widget: function(el) {
            var self = this;
            var res = $("<i class='icon-remove-sign'></i>");
            res.click(function(ev) {
                self._delete_rows($(ev.target));
                ev.preventDefault();
            });
            return res;
        },

        _add_field: function(el) {
            var self = this;
            var row = $("<tr class='managed'>");
            var td_topic = $("<td>");
            var topic = $("<input type='text' class='input-xlarge obs_topic' placeholder='Argomento'>");
            if (el[0] != "") topic.val(el[0]);
            td_topic.append(topic);

            var td_notes = $("<td>");
            var notes = $("<textarea class='input-xlarge obs_notes' placeholder='Note'>");
            if (el[1] != "") notes.val(el[1]);
            td_notes.append(notes);

            // Actions
            var td_actions = $("<td>");
            var act_delete = self._render_delete_row_widget(el);
            td_actions.append(act_delete);

            row.append(td_topic, td_notes, td_actions);
            self.rows.append(row);
        },

        _value_from_field: function() {
            var self = this;
            var val = [];
            self.rows.find("tr.managed").each(function(idx, el) {
                var el = $(el);
                var v = [
                    el.find(".obs_topic").val(),
                    el.find(".obs_notes").val(),
                ];
                val.push(v);
            });
            return val;
        },

        // If the existing row can be set to val, do it and return true. Else
        // return false.
        _update_row: function(row, val) {
            row.find(".obs_topic").val(val[0]);
            row.find(".obs_notes").val(val[1]);
            return true;
        },
    });
})( jQuery );
