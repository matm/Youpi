/*****************************************************************************
 *
 * Copyright (c) 2008-2009 Terapix Youpi development team. All Rights Reserved.
 *                    Mathias Monnerville <monnerville@iap.fr>
 *                    Gregory Semah <semah@iap.fr>
 *
 * This program is Free Software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 *****************************************************************************/

/*
 * Class: ProcessingHistoryWidget
 * Widget displaying processing history
 *
 * External Dependancies:
 *  common.js - <getSelect> function
 *  prototype.js - Enhanced Javascript library
 *
 * Constructor Parameters:
 *  container - string or DOM node: name of parent DOM block container
 *
 */
function ProcessingHistoryWidget(container) {
	// Group: Constants
	// -----------------------------------------------------------------------------------------------------------------------------


	/*
	 * Var: _id
	 * Unique instance identifier
	 *
	 */ 
	var _id = 'PHW_' + Math.floor(Math.random() * 999999);
	/*
	 * Var_: headerTitle
	 * Header box's title
	 *
	 */
	var _headerTitle = 'Processing History';
	/*
	 * Var: _container
	 * Parent DOM container
	 *
	 */ 
	var _container;
	/*
	 * Var: _sel_status_options
	 * Options titles for status DOM select
	 *
	 */ 
	var _sel_status_options = ['successful', 'failed', 'finished'];
	/*
	 * Var: _sel_sort_by_options
	 * Options titles for sorting results
	 *
	 */ 
	var _sel_sort_by_options = ['job name (A-Z)', 'date (ascending)', 'date (descending)'];


	// Group: Variables
	// -----------------------------------------------------------------------------------------------------------------------------


	/*
	 * Var: _sel_tag_options
	 * Available tags to select
	 *
	 */ 
	var _sel_tag_options = new Array();
	/*
	 * Var: _sel_tag_options
	 * Options titles for owner DOM select
	 *
	 */ 
	var _sel_owner_options = ['all', 'my'];
	/*
	 * Var: _pluginInfos
	 * Array or array of string describing plugins (used in combobox)
	 *
	 * Format:
	 *  [['scamp', 'label1'], ...]
	 *
	 */
	var _pluginInfos;
	/*
	 * Var: _maxPerPage
	 * Max number of results per page
	 *
	 */
	var _maxPerPage = 20;
	/*
	 * Var: _pageSwitcher
	 * PageSwitcher widget
	 *
	 */
	var _pageSwitcher = null;


	// Group: Functions
	// -----------------------------------------------------------------------------------------------------------------------------


	/*
	 * Function: render
	 * Call this method to render widget
	 *
	 */ 
	this.render = function() {
		_render();
	}

	/*
	 * Function: _render
	 * Main rendering function
	 *
	 */ 
	function _render() {
		var tab = new Element('table');
		tab.setAttribute('class', 'fileBrowser');
		tab.setAttribute('style', 'width: 450px;');

		var th, tr, td;
		// TR title
		tr = new Element('tr');
		th = new Element('th');
		th.insert(_headerTitle);
		tr.insert(th);
		tab.insert(tr);

		// TR input text filtering
		tr = new Element('tr');
		td = new Element('td');
		var rtab = new Element('table');
		rtab.setAttribute('class', 'results-filter');
		var rtr, rtd;
		td.insert(rtab);
		tr.insert(td);
		tab.insert(tr);

		// TR combos filtering
		rtr = new Element('tr');
		rtd = new Element('td', {nowrap: 'nowrap', colspan: 2}).addClassName('filter');
		var form = new Element('form', {id: _id + '_search_form'});
		rtd.insert(form);

		// Kind selection
		var kdiv = new Element('div').addClassName('history_type');
		var label = new Element('label').update('Type ');
		ksel = new Element('select', {id: _id + '_kind_select'});
		ksel.observe('change', function(event) {
			_onKindChange(this);
		});
		for (var k=0; k < _pluginInfos.length; k++) {
			opt = new Element('option').setStyle({
					background: "white url('/media/themes/" + guistyle + "/img/16x16/" + _pluginInfos[k][0] + ".png') no-repeat center left", 
					padding: '3px', 
					paddingLeft: '20px'
			});
			if (k == 0) opt.setAttribute('selected', 'selected');
			opt.setAttribute('value', _pluginInfos[k][0]);
			opt.insert(_pluginInfos[k][1]);
			ksel.insert(opt);
		}
		kdiv.insert(label).insert(ksel).insert(' processings');
		form.insert(kdiv);

		// Search criteria
		var tdiv = new Element('div').addClassName('history_criteria');
		label = new Element('label');
		label.insert('Show');
		tdiv.insert(label);

		var sel = getSelect(_id + '_owner_select', _sel_owner_options, 1);
		tdiv.insert(sel);

		sel = getSelect(_id + '_status_select', _sel_status_options);
		sel.options[sel.options.length-1].setAttribute('selected', 'selected');
		tdiv.insert(sel);
		label = new Element('label').update(' processings ');
		tdiv.insert(label);

		// Optional tags
		if (_sel_tag_options.length) {
			label.insert('w/images tagged ');
			var tsel = new Element('select', {id: _id + '_tags_select', multiple: true, size: 6});
			tsel.observe('click', function() {
				var sd = $(_id + '_selected_tags_div').update();
				$A(this.options).each(function(opt) {
					if (opt.selected)
						sd.insert(new Element('span', {style: opt.readAttribute('style')}).addClassName('tagwidget').update(opt.value));
				});
			});
			var opt, chk;
			$A(_sel_tag_options).each(function(tag) {
				opt = new Element('option', {value: tag.label, style: tag.css}).addClassName('tagwidget').update(tag.label);
				tsel.insert(opt);
			});
			tdiv.insert(tsel);
		}

        // Sorting order
		label = new Element('label');
		label.insert('Order results by ');
		tdiv.insert(new Element('br')).insert(label);
		var osel = new Element('select', {id: _id + '_order_select'});
        $A(_sel_sort_by_options).each(function(opt, k) {
            opt = new Element('option', {value: k}).update(opt);
            osel.insert(opt);
        });
		osel.options[osel.options.length-1].writeAttribute('selected', 'selected');
        tdiv.insert(osel);

		form.insert(tdiv);
		
		// Shows selected tags
		var pdiv = new Element('div', {id: _id + '_selected_tags_div'}).setStyle({marginBottom: '3px'});
		form.insert(pdiv);

		// Plugin-specific div (might be used by plugins for custom filtering/sorting options)
		var pdiv = new Element('div', {id: _id + '_plugin_custom_options_div'}).addClassName('plugin-filter').addClassName('history_plugin_opts');
		form.insert(pdiv);

		rtr.insert(rtd);
		rtab.insert(rtr);

		var bdiv = new Element('div', {id: _id + '_submit_div'}).addClassName('results-submit');
		var sdiv = new Element('div', {id: _id + '_stats_div', style: 'float: left;'});
		var img = new Element('img', {src: '/media/themes/' + guistyle + '/img/admin/icon_success.gif'});
		var span = new Element('span', {id: _id + '_success_span'}).setStyle({marginRight: '10px'});
		sdiv.insert(img).insert(span);
		img = new Element('img', {src: '/media/themes/' + guistyle + '/img/admin/icon_error.gif'});
		span = new Element('span', {id: _id + '_failed_span'});
		sdiv.insert(img).insert(span).insert(' ');
		span = new Element('span', {id: _id + '_total_span'}).setStyle({margin: '0px'});
		sdiv.insert(span).insert(' results on this page (out of ');
		span = new Element('span', {id: _id + '_big_total_span'}).setStyle({margin: '0px'});
		sdiv.insert(span).insert(')');
		bdiv.insert(sdiv);
		sdiv.hide();

		var rbut = new Element('input', {type: 'button', value: 'Reset'});
		rbut.observe('click', function(event) {
			$(_id + '_search_form').reset();
			_onKindChange($(_id + '_kind_select'));
			var os = $(_id + '_owner_select');
			os.options[0].selected = true;
		});
		bdiv.insert(rbut);
		var bmit = new Element('input', {type: 'button', value: 'Start searching!'});
		bmit.observe('click', function(event) {
			_applyFilter();
		});
		bdiv.insert(bmit);
		td.insert(bdiv);

		// Pages div
		pdiv = new Element('div', {id: _id + '_pages_div'}).addClassName('pagination');
		td.insert(pdiv);

		// Custom header div
		var hdiv = new Element('div', {id: _id + 'plugin_header_div'}).addClassName('pluginHeader').hide();
		td.insert(hdiv);

		// Results div
		var rdiv = new Element('div', {id: _id + '_tasks_div'}).addClassName('historyResults');
		var rt = new Element('table').setStyle({width: '100%', height: '100%'});
		var rtr, rtd;
		rtr = new Element('tr');
		rtd = new Element('td').setStyle({
			textAlign: 'center', 
			verticalAlign: 'middle', 
			color: 'lightgray', 
			fontSize: '20px',
			lineHeight: '25px'
		});
		rtd.insert('Select search criteria then<br/>hit the <i>Start searching!</i> button');
		rtr.insert(rtd);
		rt.insert(rtr);
		rdiv.update(rt);
		td.insert(rdiv);

		_container.insert(tab);
		_onKindChange(ksel);
	}

	function _onKindChange(sel) {
		// Display custom plugin filters, if any
		var d = $(_id + '_plugin_custom_options_div')
		try {
			eval(sel.options[sel.selectedIndex].value + ".addProcessingResultsCustomOptions('" + _id + "_plugin_custom_options_div');");
			d.show();
		}
		catch(e) {
			// Empty container
			d.hide();
		}
	}

	/*
	 * Function: setActivePlugins
	 * Defines list of current active plugins
	 *
	 * Required to set up processing types (filtering options)
	 *
	 * See Also:
	 *  <_pluginInfos> for format definition
	 *
	 */ 
	this.setActivePlugins = function(plugInfo) {
		_pluginInfos = plugInfo;
	}

	/*
	 * Function: _applyFilter
	 * Sends AJAX query along with search criterias; show results
	 *
	 */ 
	function _applyFilter(pageNum) {
		try {
			var ownerSel = $(_id + '_owner_select');
			var statusSel = $(_id + '_status_select');
			var kindSel = $(_id + '_kind_select');
            var sortSel = $(_id + '_order_select');
		} catch(e) { return false; }

		if (!pageNum || typeof pageNum != 'number')
			pageNum = 1;
	
		var owner = new Array();
	  	$A(ownerSel.options).each(function(opt) {
			if (opt.selected) owner.push(opt.text);
		});

		var tags = new Array();
		var tagSel = $(_id + '_tags_select');
		if (tagSel) {
			$A(tagSel.options).each(function(opt) {
				if (opt.selected) tags.push(opt.text);
			});
		}

		var status = statusSel.options[statusSel.selectedIndex].text;
		var kind = kindSel.options[kindSel.selectedIndex].value;
		var sort = sortSel.options[sortSel.selectedIndex].value;
	
		var container = $(_id + '_tasks_div');
		var xhr = new HttpRequest(
			container,
			null, // Use default error handler
			// Custom handler for results
			function(resp) {
				var r = resp.results;
				var st = resp.Stats;
				if (resp.Error) {
					var d = new Element('div').addClassName('perm_not_granted').update(resp.Error);
					container.update(d);
					return;
				}

				// Display pages
				var pdiv = $(_id + '_pages_div');
				// Page switcher widget
				if (!_pageSwitcher) {
					_pageSwitcher = new PageSwitcher(pdiv, function(page) {
						_applyFilter(page);
					});
					_pageSwitcher.setMarginsWidth(6);
				}
				else
					_pageSwitcher.setContainer(pdiv);
				_pageSwitcher.render(st.curPage, st.pageCount);

				// Display results
				container.update();
				var len = r.length;
				var tab = new Element('table').addClassName('results');
				var tr, td, cls, stab, str, std, d, img, gdiv;
	
				/*
				 * FIXME
				 * reprocess_all_failed_processing is not yet implemented in any plugin...
				 *

				if (status == 'failed' && len && kind != 'all') {
					var rdiv = new Element('div');
					rdiv.setAttribute('id', 'reprocess_failed_div');
					rdiv.setAttribute('class', 'reprocess');
					var rimg = new Element('img');
					rimg.setAttribute('onclick', kind + ".reprocess_all_failed_processings('" + resp['Stats']['TasksIds'] + "');");
					rimg.setAttribute('src', '/media/themes/' + guistyle + '/img/misc/reprocess.gif');
					rdiv.insert(rimg);
					rdiv.insert(' that current selection of processings that never succeeded');
					container.insert(rdiv);
				}
				*/

				// Notify user that results are filtered
				if (resp.filtered) {
					var msg = 'Please note that some of the results are filtered! (no read permission)';
					document.fire('notifier:notify', msg);
					var rdiv = new Element('div').addClassName('reprocess');
					rdiv.update(msg);
					container.insert(rdiv);
				}

				// Process custom plugin header for results, if any
				resp.ExtraHeader ? $(_id + 'plugin_header_div').update(resp.ExtraHeader).show() : $(_id + 'plugin_header_div').hide();

				// Updates stats
				var spans = ['success', 'failed', 'total', 'big_total'];
				for (var k=0; k < spans.length; k++) {
					var node = $(_id + '_' + spans[k] + '_span');
					node.update(resp['Stats']['nb_' + spans[k]]);
				}
				$(_id + '_stats_div').appear();
	
				if (!len) {
					tr = new Element('tr');	
					td = new Element('td');	
					td.setAttribute('style', 'color: grey; cursor: default;');
					td.innerHTML = '<h2>No results found.</h2>';
					tr.insert(td);
					tab.insert(tr);
					container.insert(tab);
					return;
				}
	
				for (var k=0; k < len; k++) {
					cls = r[k]['Success'] ?'success' : 'failure';
					tr = new Element('tr', {id: 'res_' + r[k]['Id']}).addClassName(cls);
					tr.custdata = {name: r[k]['Name'], taskId: r[k]['Id']};
					tr.observe('mouseover', function() { 
						this.removeClassName('mouseout'); 
						this.addClassName('mouseover'); 
					});
					tr.observe('mouseout', function() { 
						this.removeClassName('mouseover'); 
						this.addClassName('mouseout'); 
					});
					tr.observe('click', function() { 
						results_showDetails(this.custdata.name, this.custdata.taskId); 
						this.addClassName('clicked');
					});
					tab.insert(tr);
	
					// Description
					td = new Element('td');	
					td.innerHTML = r[k]['Title'];
					d = new Element('div');	
					td.insert(d);
					tr.insert(td);
	
					// Misc info
					stab = new Element('table');
					str = new Element('tr');	
	
					std = new Element('td');	
					std.setAttribute('nowrap', 'nowrap');
					gdiv = new Element('div');	
					gdiv.setAttribute('class', 'user');
					gdiv.insert(r[k]['User']);
					std.insert(gdiv);
	
					gdiv = new Element('div');	
					gdiv.setAttribute('class', 'node');
					gdiv.insert(r[k]['Node']);
					std.insert(gdiv);
					str.insert(std);
	
					std = new Element('td');	
					std.setAttribute('nowrap', 'nowrap');
					gdiv = new Element('div');	
					gdiv.setAttribute('class', 'clock');
					gdiv.insert(r[k]['Start']);
					gdiv.insert(new Element('br'));
					gdiv.insert(r[k]['Duration'] + ' sec');
					std.insert(gdiv);
					str.insert(std);
	
					// td.exit could contain per-plugin additionnal data
					std = new Element('td');	
					std.setAttribute('class', 'exit');
					str.insert(std);
					if (r[k].Extra) {
						std.update(r[k].Extra);
					}

					stab.insert(str);
					d.insert(stab);
					tr.insert(td);
					tab.insert(tr);
				}
				container.insert(tab);
			}
		);
	
		// Checks if a selection of that name already exists
		var post = $H({
			Owner: owner, 
			Status: status, 
			Kind: kind,
			Limit: _maxPerPage,
			SortBy: sort,
			Page: pageNum,
			Tag: tags
		});

		// Add POST data info related to custom plugin search criteria, if any
		var cdiv = $(_id + '_plugin_custom_options_div');
		if (!cdiv.empty()) {
			var elems = cdiv.select('[name]');
			elems.each(function(elem) {
				post.set(elem.readAttribute('name'), elem.value);
			});
		}
	
		// Send HTTP POST request
		xhr.setBusyMsg('Please wait while filtering data...');
		xhr.setCustomAnimatedImage('/media/themes/' + guistyle + '/img/misc/snake-loader.gif');
		xhr.send('/youpi/results/filter/', post.toQueryString());
	}

	/*
	 * Function: applyFilter
	 * Public method for <_applyFilter>
	 *
	 */ 
	this.applyFilter = function(pageNum) {
		_applyFilter(pageNum);
	}

	/*
	 * Function: addFromSource
	 * Add a 'from' source in the _sel_owner_options array
	 *
	 * Parameters:
	 *  name - string: name to add
	 *
	 */ 
	this.addFromSource = function(name) {
		if (typeof name != 'string')
			throw 'Name must be a string!'
		_sel_owner_options.push(name);
	}

	/*
	 * Function: addTag
	 * Add a 'tag' source in the _sel_tag_options array
	 *
	 * Parameters:
	 *  label - string: tag label
	 *  style - string: CSS value [optional]
	 *
	 */ 
	this.addTag = function(label, style) {
		if (typeof label != 'string')
			throw 'Name must be a string!'
		if (style && typeof style != 'string')
			throw 'Style must be a string!'

		_sel_tag_options.push({label: label, css: style ? style : null});
	}

	/*
	 * Function: _error
	 * Displays an alert error message
	 *
	 * Parameters:
	 *  msg - string: error message to display
	 *
	 */ 
	function _error(msg) {
		alert('ProcessingHistoryWidget: ' + msg);
	}

	/*
	 * Function: _render
	 * Main rendering function
	 *
	 */ 
	function _main() {
		if (!container) {
			_error("Container is null!");
			return;
		}

		if (typeof container == 'string') {
			var cont = $(container);
			if (!cont) {
				_error('not a valid container: ' + container);
				return;
			}
			_container = cont;
		}
		else if (typeof container == 'object') {
			_container = container;
		}
		else {
			_error('Bad container type: ' + typeof container);
			return;
		}
	}

	_main();
}
