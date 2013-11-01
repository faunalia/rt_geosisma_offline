/*
# -*- coding: utf-8 -*-
# Copyright (C) 2013 Luigi Pirelli (luipir@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
* */

// Call fun(row, col) with row in [firstrow, lastrow] and col in each
// letter in cols
function foreachrc(firstrow, lastrow, cols, fun)
{
    var names = cols.split("")
    for (var i = firstrow; i <= lastrow; ++i)
        for (var j = 0; j < names.length; ++j)
            fun(i, names[j])
}

// Return an array with all input elements inside \a main whose ID matches or
// not matches a whitelist and/or a blacklist regexp
function sub_elements(main, wl_re, bl_re)
{
    var res = [];
    main.find("input").each(function(idx, el) {
        if (wl_re != null && !el.id.match(wl_re))
            return;
        if (bl_re != null && el.id.match(bl_re))
            return;
        res.push($(el));
    });
    return res;
}

function refresh_attachments()
{
    $.getJSON("/safety/attachment_list/" + $("#safety_id").val(),
            function(data){
                var master = $("#attachments")
                master.empty()
                var ul = $("<ul>")
                $.each(data.res, function(i, item){
                    if (i == 0)
                    {
                        master.append("<h2>Attachments</h2>")
                        master.append(ul)
                    }
                    var li = $("<li>")
                    var a = $("<a>")
                              .attr("href", "/safety/attachment/"+item.id)
                              .text(item.name)
                    if (item.type.substr(0, 6) == "image/")
                        a.click(function() {
                            var preview = $("#attachment_preview")
                            preview.empty()
                            preview.append($("<img>")
                                           .attr("src", "/safety/attachment/"+item.id))
                            return false
                        })
                    li.append(a)
                    li.append(" ")
                    li.append($("<a>")
                              .attr("href", "#")
                              .text("[del]")
                              .click(function() {
                                  $.getJSON("/safety/attachment_del/" + $("#safety_id").val() + "/" + item.id,
                                      function(data) { refresh_attachments() })
                                  return false
                              }))
                    ul.append(li)
                });
            }
    );
}

// Pad numbers with trailing digits to be 'count' characters long
function numpad(val, count)
{
    if (val == null || val == "") return null

    var res = val.toString()
    while (res.length < count)
        res = "0" + res
    return res
}

function update_safety_number()
{
    $.get("/safety/valid_report_number", { safety_id: $("#safety_id").val(), safety_date: $("#date").val() },
            function(data)
            {
                $("#number").val(data)
                $("span.footer_number").text(data)
            }
    );
    return false;
}


// https://labs.truelite.it/issues/2123

function fill_fields_from_map(e)
{
    // Get the geographic coordinates of the clicked point
    var lon_lat = map.getLonLatFromPixel(e.xy);
    //console.log(lon_lat);
    // show the spinner
    $("#ajax_loader").show();
    // Get the data from the database
    $.ajax({
            url:     "/missions/get_catasto_data/",
            data:    { lon: lon_lat.lon, lat: lon_lat.lat },
            success: function(catasto_values)
            {
                // Set the fields in the safety report page
                $.each(catasto_values, function(i, elem) {
                    //console.log(i, elem);
            var nel = $("#"+elem.id);
            nel.val(elem.value);
            nel.change();
                });
            },
            complete: function() {
               $("#ajax_loader").hide();
            },
    });
}

function select_from_map()
{
    //console.log(map);
    // Test if the s1catpart1 field is disabled when the user clicks...
    if ($("#s1catfoglio").prop('disabled')) {
        // Enable all the s1 input fields and unregister click listener in map
        $("#s1 input").prop('disabled', false);
        map.events.unregister("click", map, fill_fields_from_map);
        $('#select_from_map').text('Seleziona dalla mappa');
    }
    else {
        // Else disable text input fields and add the click listener
        $("#s1 input").prop('disabled', true);
        // http://www.subclosure.com/openlayers-add-mouse-click-event-listener-to-a-map.html
        // Add a listener for the click event
        map.events.register("click", map, fill_fields_from_map);
        $('#select_from_map').text('Correggi i campi a mano');
    }
}



    /*
     * Queue of checked checkboxes, that will uncheck the old ones if it
     * reaches a maximum size.
     */
    var BoundedCheckboxQueue = function (max) {
        var self = this;
        self.queue = [];
        self.changed = function(field_id) {
            // Check if the field is already in the queue, and remove it
            var pos = $.inArray(field_id, self.queue);
            if (pos != -1)
                // Remove it from the array if it is
                self.queue.splice(pos, 1);

            if ($("#" + field_id).prop("checked"))
            {
                // If the field has been checked, add it to the array
                self.queue.push(field_id);

                // If the array is too long, uncheck the old elements
                while (self.queue.length > max)
                {
                    var head = self.queue.shift();
                    $("#" + head).subfield_checkbox("uncheck");
                }
            }
        };
        return this;
    };

    // s2cer* allow max 2 elements
    var s2cerlimit = BoundedCheckboxQueue(2);

$(function() {
    var data = {a:1};
    var safety = $("#id_safety");
    safety.jsonfield();
    //safety.jsonfield({debug_submit: true});
    $(".NullableUnicodeField").subfield_text({"master": safety});
    $(".NullableIntField").subfield_int({"master": safety});
    $(".IntHiddenField").subfield_int({"master": safety});
    $(".NullableFloatField").subfield_float({"master": safety});
    $(".FloatHiddenField").subfield_float({"master": safety});
    $(".NullableIntLabeledRadioField").subfield_radio({"master": safety});
    $(".NullableIntRadioField").subfield_radio({"master": safety});
    $(".CheckBoxField").subfield_checkbox({"master": safety});
    $(".DateField").subfield_text({"master": safety});
    $(".TextAreaField").subfield_text({"master": safety});
    $(".ObservationsField").subfield_observations({"master": safety});

    // Autocomplete common bits

    var api_url = '/api/v1/';
    var get_autocomplete = function(name, query, on_result) {
        // set asyncronous ajax call
        var data = $.extend({
            "format": "json",
            "limit": 0,
        }, query);
        console.log(query.toponimo__istartswith)
        return $.getJSON(offline_autocomplete.get( name, JSON.stringify(data) ), data, on_result);
    };

    // Setup autocompletion

    var sf_set = function(field, val) {
        $(field).data("poly_subfield").set(val);
    };

    $("#s1prov").autocomplete({
        source: function(req, resp) {
            // Example URL: http://localhost:8000/api/v1/provincia/?format=json&limit=0&sigla__startswith=B
            get_autocomplete("provincia/", {
                    "toponimo__istartswith": req.term,
                }, function(data) {
                    var res = $.map(data.objects, function(el, idx) {
                        return {
                            data: el,
                            value: el.sigla,
                            label: el.toponimo,
                        };
                    });
                    resp(res);
                });
        },
        select: function(ev, ui) {
            ev.preventDefault();
            var val = ui.item.data;
            if ($(this).val() != val.sigla)
            {
                sf_set("#s1com", null);
            }
            sf_set(this, val.sigla);
            sf_set("#s1istatreg", val.idregione);
            sf_set("#s1istatprov", val.id_istat);
            $("#footer_istat_prov").text(val.id_istat);
        },
    });

    $("#s1com").autocomplete({
        source: function(req, resp) {
            // Example URL: http://localhost:8000/api/v1/comune/?format=json&limit=10&provincia__sigla=BO&toponimo__istartswith=San
            var q = { "toponimo__istartswith": req.term };
            var prov = $("#s1prov").val();
            if (prov) q["provincia__sigla"] = prov;
            get_autocomplete("comune/", q, function(data) {
                    var res = $.map(data.objects, function(el, idx) {
                        return {
                            data: el,
                            value: el.toponimo,
                            label: el.toponimo,
                        };
                    });
                    resp(res);
                });
        },
        select: function(ev, ui) {
            ev.preventDefault();
            var val = ui.item.data;
            if ($(this).val() != val.toponimo)
            {
                sf_set("#s1loc", null);
            }
            sf_set(this, val.toponimo);
            sf_set("#s1istatcom", val.id_istat);
            $("#footer_istat_com").text(val.id_istat);
            // Query to zoom for Comune. Table 'comune' doesn't have the_geom,
            // so I have to pass through a couple of JOINs.
            // refs #2108 https://labs.truelite.it/issues/2108
            var q = { "limit": 10, "format": "json", "belfiore__comune__id_istat": val.id_istat };
            //$.getJSON(api_url + "catasto2010_1/", q, function(data) {
            $.getJSON(offline_autocomplete.get( "catasto2010_1/" , JSON.stringify(q) ), q, function(data) {
                var geoms = $.map(data.objects, function(el) { return el.the_geom });
                var c = OpenLayers.Geometry.fromWKT(geoms);
                var bounds = c.getBounds();
                map.zoomToExtent(bounds);
            });
        },
    });

    $("#s1loc").autocomplete({
        source: function(req, resp) {
            // Example URL: http://localhost:8000/api/v1/localita/?format=json&limit=10&cod_pro=046&cod_com=023
            var q = { "denom_loc__istartswith": req.term };
            var prov = $("#s1istatprov").val();
            if (prov) q["cod_pro"] = prov;
            var com = $("#s1istatcom").val();
            if (com) q["cod_com"] = com;
            get_autocomplete("localita/", q, function(data) {
                var res = $.map(data.objects, function(el, idx) {
                    return {
                        data: el,
                        value: el.denom_loc,
                        label: el.denom_loc + " ("+el.sez2001.substring(el.sez2001.length-3)+")",
                    };
                });
                resp(res);
            });
        },
        select: function(ev, ui) {
            ev.preventDefault();
            var val = ui.item.data;
            sf_set(this, val.denom_loc);
            sf_set("#s1istatloc", val.cod_loc);
            sf_set("#s1istatcens", val.sez2001.substring(val.sez2001.length-3));
            var geom = OpenLayers.Geometry.fromWKT(val.the_geom);
            var bounds = geom.getBounds();
            map.zoomToExtent(bounds);
        },
    });

    var USAGES = [
        { value: "00", label: "Strutture per l'istruzione" },
        { value: "01", label: "Nido" },
        { value: "02", label: "Scuola Materna" },
        { value: "03", label: "Scuola elementare" },
        { value: "04", label: "Scuola Media Inferiore-obbligo" },
        { value: "05", label: "Scuola Media Superiore" },
        { value: "06", label: "Liceo" },
        { value: "07", label: "Istituto Professionale" },
        { value: "08", label: "Istituto Tecnico" },
        { value: "09", label: "Università (Facoltà umanistiche)" },
        { value: "10", label: "Università (Facoltà scientifiche)" },
        { value: "11", label: "Accademia e conservatorio" },
        { value: "12", label: "Uffici Provveditorato e Rettorato" },
        { value: "20", label: "Strutture Ospedaliere e sanitarie" },
        { value: "21", label: "Ospedale" },
        { value: "22", label: "Casa di cura" },
        { value: "23", label: "Presidio sanitario-Ambulatorio" },
        { value: "24", label: "A.S.L. (Azienda Sanitaria)" },
        { value: "25", label: "INAM - INPS e simili" },
        { value: "30", label: "Attività collettive civili" },
        { value: "31", label: "Stato (uffici tecnici)" },
        { value: "32", label: "Stato (Uffici Amministrativi, finanziari)" },
        { value: "33", label: "Regione" },
        { value: "34", label: "Provincia" },
        { value: "35", label: "Comunità Montana" },
        { value: "36", label: "Municipio" },
        { value: "37", label: "Sede Comunale decentrata" },
        { value: "38", label: "Prefettura" },
        { value: "39", label: "Poste e Telegrafi" },
        { value: "40", label: "Centro Civico- Centro per riunioni" },
        { value: "41", label: "Museo-Biblioteca" },
        { value: "42", label: "Carceri" },
        { value: "50", label: "Attività collettive militari" },
        { value: "51", label: "Forze Armate (escluso i carabinieri)" },
        { value: "52", label: "Carabinieri e Pubblica sicurezza" },
        { value: "53", label: "Vigili del fuoco" },
        { value: "54", label: "Guardia di Finanza" },
        { value: "55", label: "Corpo Forestale dello Stato" },
        { value: "60", label: "Attività Collettive Religiose" },
        { value: "61", label: "Servizi parrocchiali" },
        { value: "62", label: "Edifici per il culto" },
        { value: "70", label: "Attività per i servizi Tecnologici a rete" },
        { value: "71", label: "Acqua" },
        { value: "72", label: "Fognature" },
        { value: "73", label: "Energia Elettrica" },
        { value: "74", label: "Gas" },
        { value: "75", label: "Telefoni" },
        { value: "76", label: "Impianti per telecomunicazioni" },
        { value: "80", label: "Strutture per mobilità e trasporto" },
        { value: "81", label: "Stazione ferroviaria" },
        { value: "82", label: "Stazione autobus" },
        { value: "83", label: "Stazione aeroportuale" },
        { value: "84", label: "Stazione navale" },
    ];
    $("#s1coduso").autocomplete({
        source: USAGES,
        select: function(ev, ui) {
            ev.preventDefault();
            var val = ui.item.value;
            sf_set(this, val);
        },
    });

    // Zoom to map when changing particelle and/or foglio
    safety.jsonfield("value_trigger", function(data) {
        return ""+data["s1catpart1"]+":"+data["s1catfoglio"];
    }, function(val, data) {
        var query = {
            "format": "json",
            "limit": 0,
        };

        if (!data["s1istatprov"] || !data["s1istatcom"] || !data["s1catfoglio"] || !data["s1catpart1"])
            return;

        query["belfiore__provincia__id_istat"] = data["s1istatprov"];
        query["belfiore__comune__id_istat"]    = data["s1istatcom"];
        query["foglio"] = data["s1catfoglio"];
        query["codbo"]  = data["s1catpart1"];

        console.log("PART_CHANGED", data, query);

        // Piazza al Serchio (LU) foglio=1 belfiore="G582", part 10 to 19 are all good

        $.getJSON(offline_autocomplete.get( "catasto2010_2/" , JSON.stringify(query) ), query, function(data) {
            console.log("catasto", data);
            var geoms = $.map(data.objects, function(el) { return el.the_geom });
            if(geoms.length > 0) {
                var c = OpenLayers.Geometry.fromWKT(geoms[0]);
                var bounds = c.getBounds();
                map.zoomToExtent(bounds);
            } else {
                alert("Dato foglio/particella non rilevato in archivio");
            }
        });
    });

    $("#s1istatprov").change(function() {
            $("#footer_istat_prov").text(this.value);
    }).change()
    $("#s1istatcom").change(function() {
            $("#footer_istat_com").text(this.value);
    }).change()
    $("#sdate").change(function() {
            $("#footer_date").text(this.value);
            // TODO: update_safety_number();
    }).change()
    $("#number").change(function() {
            $("span.footer_number").text(this.value)
    }).change()
    $("#s1number_update").click(update_safety_number);

    // Install form validation hooks

    // Enable/disable particelle according to other fields
    // The particelle query needs provincia, comune, foglio.
    var slaves = [];
    for (var i = 1; i <= 4; ++i)
        slaves.push($("#s1catpart" + i));

    safety.jsonfield("value_trigger", function(data) {
        return ""+data["s1istatprov"]+":"+data["s1istatcom"]+":"+data["s1catfoglio"];
    }, function(val, data) {
        if (data["s1istatprov"] && data["s1istatcom"] && data["s1catfoglio"]) {
            $.each(slaves, function(idx, elem) {
                elem.removeAttr("disabled");
            });
        }
        else {
            $.each(slaves, function(idx, elem) {
                elem.attr("disabled", "disabled");
            });
        }
    });

    for (var i = 1; i <= 8; ++i) {
    var e = $("#s2cer"+i);
    if(e.attr('checked')) {
        s2cerlimit.changed("s2cer"+i);
        console.log(e, "CHECKED!");
    }
        e.change(function(ev) { s2cerlimit.changed(this.id) });
    }
    // Enable/disable fields based on values of other fields
    for (var i = 1; i <= 8; ++i)
        safety.jsonfield("disable_when_false", "s2uso" + i, $("#s2uson" + i));

    // Only enable s1vcother when s1viacorso is 5
    (function() {
        var slave = $("#s1vcother").data("poly_subfield");
        safety.jsonfield("value_trigger", function(data) { return data["s1viacorso"] != "5"; }, function(val, data) {
            slave.disable("enforce_s1vc", val);
        });
    })();

    // Sezione 3: tipologia

    // Constraint: when some Altre Strutture is selected, strutture in
    // muratura is disabled
    (function() {
        var slaves = [];
        foreachrc(1, 6, "BCDE", function (row, col) {
            slaves.push($("#s3t" + col + row).data("poly_subfield"));
        });

        safety.jsonfield("value_trigger", function(data) {
            return data["s3as1"] || data["s3as2"] || data["s3as3"];
        }, function(val, data) {
            $.each(slaves, function(idx, el) { el.disable("altrestrutture", val); });
        });
    })();

    (function() {
        var a1slaves = [];
        foreachrc(1, 6, "ABCDE", function (row, col) {
            if (row == 1 && col == "A") return;
            a1slaves.push($("#s3t" + col + row));
        });

        // Constraint: when A1 is selected, the rest is unselected and disabled
        safety.jsonfield("disable_when_true", "s3tA1", a1slaves);

        // Constraint: when Non identificate is selected in a column, the
        // rest of the column is disabled
        $.each("BCDE".split(""), function(idx, el) {
            var slaves = [];
            for (var i = 2; i <= 6; ++i)
                slaves.push($("#s3t" + el + i));

            safety.jsonfield("disable_when_true", "s3t" + el + "1", slaves);
        });

        // Constraint: when Non identificate is selected in a row, the
        // rest of the row is disabled
        for (var i = 2; i <= 6; ++i)
        {
            var slaves = [];
            $.each("BCDE".split(""), function(idx, el) {
                slaves.push($("#s3t" + el + i));
            });

            safety.jsonfield("disable_when_true", "s3tA" + i, slaves);
        }

        // Constraint: no more than 2 strutture checkboxes can be selected
        safety.jsonfield("value_trigger", function(data) {
            var count = 0;
            foreachrc(1, 6, "ABCDE", function (row, col) {
                if (row == 1 && col == "A") return;
                if (data["s3t" + col + row]) ++count;
            });
            return count >= 2;
        }, function(val, data) {
            if (val)
            {
                // disable all the unchecked ones
                $.each(a1slaves, function(idx, el) {
                    var ps = el.data("poly_subfield");
                    if (!ps.get())
                        ps.disable("enforce_max2", true);
                });
            } else {
                // enable all of them
                $.each(a1slaves, function(idx, el) {
                    el.data("poly_subfield").disable("enforce_max2", false);
                });
            }
        });
    })();

    // Sezione 4: danni

    // Disable checkboxes in s4 "danno" if 'Nullo' is checked
    for (var i = 1; i <= 6; ++i)
        safety.jsonfield("disable_when_true", "s4dL" + i, sub_elements($("#s4d"), new RegExp("^s4d[A-I]"+i)));

    // Disable checkboxes in s4 "provvedimenti" if 'Nessuno' is checked
    for (var i = 1; i <= 5; ++i)
        safety.jsonfield("disable_when_true", "s4pA" + i, sub_elements($("#s4d"), new RegExp("^s4p[B-F]"+i)));

    // Constraint: the sum of selected items in a row must not exceed 3/3
    for (var row = 1; row <= 6; ++row)
    {
        // Value of each element
        //var values = [ 2.25, 1.25, 0.25, 2.25, 2.15, 0.25, 2.25, 1.25, 0.25 ];
    var values = [ 3,2,1,3,2,1,3,2,1];

        (function(row) {
        // List the elements
        var items = sub_elements($("#s4d"), new RegExp("^s4d[A-I]" + row));

        safety.jsonfield("value_trigger", function(data) {
            // Count the total value for this row
            var count = 0;
            $.each("ABCDEFGHI".split(""), function(idx, col) {
                if (data["s4d" + col + row])
                    count += values[idx];
            });
            return count;
        }, function(count, data) {
            // Disable all the fields that would make the row have more than 3,
            // and enable all others
            $.each(items, function(idx, el) {
                var ps = el.data("poly_subfield");
                if (!ps.get() && count + values[idx] > 5)
                    ps.disable("enforce_max3_3", true);
                else
                    ps.disable("enforce_max3_3", false);
            });
        });
        })(row);
    }

    // Sezione 5

    // Constraint: if B is checked, C..G are disabled

    for (var row = 1; row <= 6; ++row) {
        safety.jsonfield("disable_when_true", "s5ensB" + row, sub_elements($("#s5tbl"), new RegExp("^s5ens[C-G]" + row)));
    }

    // Sezione 8: giudizio di agibilità

    // Constraint: disable input fields if the building is ok
    (function() {
        var slaves = [$("#s8inag"), $("#s8famev"), $("#s8persev")];
        safety.jsonfield("value_trigger", function(data) { return data["s8agibilita"] == "0"; }, function(val, data) {
            $.each(slaves, function(idx, el) {
                el.data("poly_subfield").disable("enforce_s8agi", val);
            });
        });
    })();

    // Sezione 8: accuratezza della visita

    // Constraint: disable a-e unless 4 is selected
    (function() {
        var slaves = [];
        for (var i = 0; i <= 4; ++i) slaves.push($("#s8whynot_" + i));

        safety.jsonfield("value_trigger", function(data) { return data["s8accuracy"] != "3"; }, function(val, data) {
            $.each(slaves, function(idx, el) {
                el.data("poly_subfield").disable("enforce_s8acc_ae", val);
            });
        });
    })();

    // Constraint: disable #s8whyother unless e is selected
    (function() {
        var slave = $("#s8whyother").data("poly_subfield");
        safety.jsonfield("value_trigger", function(data) { return data["s8whynot"] != "4"; }, function(val, data) {
            slave.disable("enforce_s8whynot_4", val);
        });
    })();


    // Sezione 8: provvedimenti di P.I. suggeriti

    // Constraint: the two 'other' fields are only enabled if one of the two
    // radis is enabled
    safety.jsonfield("disable_when_false", "s8prov11", [$("#s8prov11other")]);
    safety.jsonfield("disable_when_false", "s8prov12", [$("#s8prov12other")]);

    // Machinery to fill provvedimenti urgenti
    (function() {
        var data = safety.data("jsonfield");

        var s8pu_root = $("#s8pu_main");
        var s8pu_public = $("#s8pu_public", s8pu_root);
        var s8pu_private = $("#s8pu_private", s8pu_root);
        var s8pu_denom = $("#s8pu_denom", s8pu_root);
        var s8pu_via = $("#s8pu_via", s8pu_root);
        var s8pu_paese = $("#s8pu_paese", s8pu_root);
        var s8pu_coduso = $("#s8pu_coduso", s8pu_root);
        var s8pu_number = $("#s8pu_number", s8pu_root);
        var s8pu_date = $("#s8pu_date", s8pu_root);

        var make_via = function()
        {
            var vc = data.get("s1viacorso");
            var via = data.get("s1via");
            var civico = data.get("s1civico");
            if (vc < 5)
                vc = ["via", "corso", "vicolo", "piazza"][vc - 1];
            else
                vc = data.get("s1vcother");

            if (vc == undefined)
                vc = ""
            if (via == undefined)
                via = ""
            if (civico == undefined) 
                civico = ""
            return vc + " " + via + " " + civico;
        };

        $("#s8pu_toggle").click(function(ev) {
            // Proprietà: s2prop
            var s8prop = safety.data("jsonfield").get("s2prop");
            s8pu_public[0].checked = (s8prop == 0);
            s8pu_private[0].checked = (s8prop == 1);
            // Denominazione: s1name
            s8pu_denom.text(data.get("s1name"));
            // Indirizzo: dalla sezione 1
            s8pu_via.text(make_via());
            s8pu_paese.text(data.get("s1com") + " (" + data.get("s1prov") + ")");
            // Destinazione uso: s1coduso
            var coduso = data.get("s1coduso");

            if(coduso != undefined  && coduso.length > 0) {
                s8pu_coduso.text("S"+data.get("s1coduso"));
            } else {
                var coduso_text = ""
                var descs = new Array();
                descs[1] = 'Abitativo';
                descs[2] = 'Produttivo';
                descs[3] = 'Commercio';
                descs[4] = 'Uffici';
                descs[5] = 'Serv. Pub.';
                descs[6] = 'Deposito';
                descs[7] = 'Strategico';
                descs[8] = 'Turis-ricet.';
            
                for(var i = 1; i < 9; i++) {
                    var item = "s2uso"+i;
                    var item_data = data.get(item);
                    if(item_data) {
                        coduso_text = coduso_text + " "+descs[i];
                    }
                }
                s8pu_coduso.text(coduso_text);
                
            }
            // Rif scheda: numero e data scheda
            s8pu_number.text(data.get("number"));
            s8pu_date.text(data.get("sdate"));
            s8pu_root.toggle();
            ev.preventDefault();
        });
        s8pu_root.hide();
    })();

    /*
    $("#s9obs_extend").click(function() {
        // Row where the extend button is: we add the new row before that one
        var tailrow = $("#s9obs_extend").closest("tr")
        // Use the first row as a template
        var template = $("#s9obs_topic").first().closest("tr")
        // Clone the template an empty its fields
        var newrow = template.clone()
        newrow.find("input").attr("value", null)
        // Insert it
        newrow.insertBefore(tailrow)
        return false
    })


    $("#addattachment").ajaxForm({
            target: "#addattachmentresult",
            dataType: "json",
            success: function(responseText, statusText, xhr, form) {
              $("#addattachment")[0].reset()
              refresh_attachments()
            }
    })

    refresh_attachments()
*/
});
