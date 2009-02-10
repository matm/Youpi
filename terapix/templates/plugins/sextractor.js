// JS code for Sextractor plugin


var uidsex = '{{ plugin.id }}';
var {{ plugin.id }} = {
	/*
	 * Variable: ims
	 *
	 * <ImageSelector> instance
	 *
	 */
	ims: null,


	addSelectionToCart: function() {
		//Checks for images
		sels = {{ plugin.id }}.ims.getListsOfSelections();
		console.log(sels);	

		if (!sels) {
			alert('No images selected. Nothing to add to cart !');
			return;
		}

		// OPTIONAL
		var optPath = new Array();
		var optSel = $(uidsex + '_flags_select', uidsex + '_weights_select', uidsex + '_psf_select');
		
		optSel.each(function(select, j) {
			if (optSel[j] == null) { 
				return;
			}
			else {
				var path = select.options[select.selectedIndex].text;
				if (path != selector.getNoSelectionPattern()) {
					optPath[j] = path;
				}
			}
		});
		

		var total = {{ plugin.id }}.ims.getImagesCount();
		
		//Get config file
		var cSel = $(uidsex + '_config_name_select');
		var config = cSel.options[cSel.selectedIndex].text;

		//Gets custom output directory
		var custom_dir = $('output_path_input').value.strip().gsub(/\ /, '');
		var output_data_path = '{{ processing_output }}{{ user.username }}/' + uidsex + '/';

		if (custom_dir) 
			output_data_path += custom_dir + '/';

		{{ plugin.id }}.do_addSelectionToCart({
			config: config, 
			imgList: sels,
			weightPath: optPath[1],
			flagPath: optPath[0],
			psfPath: optPath[2],
			resultsOutputDir: output_data_path
		});
	},

	do_addSelectionToCart: function(data) {
		var total = {{ plugin.id }}.ims.getImagesCount();


		// Finally, add to the shopping cart
		p_data = {	plugin_name : uidsex , 
					userData 	: data
		};

		s_cart.addProcessing(	p_data,
								// Custom handler
								function() {
									alert('The current image selection (' + total + ' ' + (total > 1 ? 'images' : 'image') + 
										') has been\nadded to the cart.');
								}
		);

	},

	/*
	 * Function displayImageCount
	 * Renders list of images to be processed as a summary (used in the shopping cart plugin rendering)
	 *
	 * Parameters:
	 *
	 * imgList - array of arrays of idLists
	 *
	 */
	displayImageCount: function(imgList, container_id) {
		var container = $(container_id);
		var imgList = eval(imgList);
		var c = 0;
		var txt;
		imgList.length > 1 ? txt = 'Batch' : txt = 'Single';
		var selDiv = new Element('div', {'class': 'selectionModeTitle'}).update(txt + ' selection mode:');
		container.insert(selDiv);

		selDiv = new Element('div', {'class': 'listsOfSelections'});

		for (var k=0; k < imgList.length; k++) {
			c = imgList[k].toString().split(',').length;
			if (imgList.length > 1)
				txt = 'Selection ' + (k+1) + ': ' + c + ' image' + (c > 1 ? 's' : '');
			else
				txt = c + ' image' + (c > 1 ? 's' : '');

			selDiv.update(txt);
			selDiv.insert(new Element('br'));
		}
		container.insert(selDiv);
	},


	/*
	 * Function: run
	 * Run processing
	 *
	 * Parameters:
	 *	name - string: name part of ID 
	 *  row - integer: for row number
	 *
	 */ 
	run: function(trid, opts, silent) {
		var silent = typeof silent == 'boolean' ? silent : false;
		var runopts = get_runtime_options(trid);
		var logdiv = $('master_condor_log_div');
	
		var r = new HttpRequest(
				logdiv,
				null,	
				// Custom handler for results
				function(resp) {
					r = resp['result'];
					var success = update_condor_submission_log(resp, silent);
					if (!success) return;
	
					// Silently remove item from the cart
					removeItemFromCart(trid, true);
				}
		);
	
		// Adds various options
		opts = $H(opts);
		opts.set('Plugin', uidsex);
		opts.set('Method', 'process');
		opts.set('ReprocessValid', (runopts.reprocessValid ? 1 : 0));

		var post = getQueryString(opts) +
			'&' + runopts.clusterPolicy;

		r.send('/youpi/process/plugin/', post);
	},

	reprocessAllFailedProcessings: function(tasksList) {
		alert('TODO...');
	},

	renderOutputDirStats: function(container_id) {
		var container = $(container_id).update();
	
		// global var defined in results.html
		var resp = output_dir_stats_data;
		var stats = resp['Stats'];
	
		var tab = new Element('table', {'class': 'output_dir_stats'});
		var tr,th,td;
		var tr = new Element('tr');
		// Headers
		var headers = $H({	task_success: 'Task success',
							task_failure: 'Task failures',
							task_total: 'Total processings'
		});
		headers.each(function(header) {
			th = new Element('th', {'class': header.key, 'colspan': '2'}).update(header.value);
			tr.insert(th);
		});
		tab.insert(tr);
	
		tr = new Element('tr');
		var val, percent, cls;
		headers.each(function(header, k) {
			switch (k) {
				case 0:
					val = stats['TaskSuccessCount'][0];
					percent = stats['TaskSuccessCount'][1] + '%';
					cls = 'task_success';
					break;
				case 1:
					val = stats['TaskFailureCount'][0];
					percent = stats['TaskFailureCount'][1] + '%';
					cls = 'task_failure';
					break;
				case 2:
					val = stats['Total'];
					percent = '100%';
					cls = 'task_total';
					break;
				default:
					break;
			}
			var td = new Element('td', {'class': cls}).update(val);
			tr.insert(td);

			td = new Element('td', {'class': cls}).update(percent);
			tr.insert(td);
		});
		tab.insert(tr);
		container.insert(tab);
	},

	saveItemForLater: function(trid, opts, silent) {
	//idList, itemId,flagPath, weightPath, psfPath, resultsOutputDir, config, silent) {
		opts = $H(opts);
		opts.set('Plugin', uidsex);
		opts.set('Method', 'saveCartItem');

		var runopts = get_runtime_options(trid);
		var r = new HttpRequest(
				uidsex + '_result',
				null,	
				// Custom handler for results
				function(resp) {
					// Silently remove item from the cart
					removeItemFromCart(trid, true);
					// Global function (in shoppingcart.html)
					showSavedItems();
				}
		);
	
		var post = getQueryString(opts);
		r.send('/youpi/process/plugin/', post);
	},

	/*
	 * Displays custom result information. 'resp' contains 
	 * server-side info to display
	 *
	 */
	resultsShowEntryDetails: function(container_id) {
		var tr, th, td;
		// See templates/results.html, function showDetails(...)
		var resp = currentReturnedData;
		var container = $(container_id);
		var d = new Element('div', {'class': 'entryResult'});
		var tab = new Element('table', {'class': 'fileBrowser', 'style': 'width: 100%'});
	
		tr = new Element('tr');
		th = new Element('th').update(resp['Title']);
		tr.insert(th);
		tab.insert(tr);
	
		// Duration
		var tdiv = new Element('div', {'class': 'duration'});
		tdiv.insert(resp['Start'] + '<br/>');
		tdiv.insert(resp['End'] + '<br/>');
		var src;
		resp['Success'] ? src = 'success' : src = 'error';
		var img = new Element(	'img', {src: '/media/themes/{{ user.get_profile.guistyle }}/img/admin/icon_' + src + '.gif',
										style: 'padding-right: 5px;'
		});
		tdiv.insert(img);
		tdiv.insert(resp['Duration']);
		tr = new Element('tr');
		td = new Element('td', {style: 'border-bottom: 2px #5b80b2 solid'});
		td.insert(tdiv);
		tr.insert(td);
		tab.insert(tr);
	
		// User
		var udiv = new Element('div', {'class': 'user'});
		udiv.insert('Job initiated by ' + resp['User']);
		udiv.insert(new Element('br'));
		udiv.insert('Exit status: ');
		udiv.insert(new Element('br'));
		var txt;
		resp['Success'] ? txt = 'success' : txt = 'failure';
		var exit_s = new Element('span', {'class': 'exit_' + txt}).update(txt);
		udiv.insert(exit_s);
		td.insert(udiv);
	
		tr = new Element('tr');
		td = new Element('td', {style: 'padding: 0px'});
		var tab2 = new Element('table', {'class': 'qfits-result-entry-params'});
		td.insert(tab2);
		tr.insert(td);
		tab.insert(tr);

		// Thumbnails when successful
		if (resp.Success) {
			tr = new Element('tr', {'class': 'scamp-result-entry-tn'});
			td = new Element('td', {
					onclick: "window.open('" + resp['WWW'] + "sex.xml');",
					onmouseover: "this.setAttribute('class', 'scamp-result-entry-complete-on');",
					onmouseout: "this.setAttribute('class', 'scamp-result-entry-complete-off');",
					'class': 'scamp-result-entry-complete-off'
			});
			td.update('See SEx XML file');
			tr.insert(td);
	
			td = new Element('td');
			var tn, imgpath, a;
			resp.Previews.each(function(thumb, k) {
				imgpath = resp.WWW + thumb;
				a = new Element('a', { href: imgpath.replace(/tn_/, ''), rel: 'lightbox[sex]', title: 'Sources extracted images' });
				tn = new Element('img', {
					src: resp.HasThumbnails ? imgpath : imgpath.replace(/tn_/, ''),
					'class' : 'scamp-result-entry-tn'
				}).hide();
				// Adds a cool fade-in effect
				$(tn).appear({duration: k/3});
	
				if (!resp.HasThumbnails)
					tn.setAttribute('width', '60px');
	
				a.insert(tn);
				td.insert(a);
			});
			tr.insert(td);
			tab2.insert(tr);
		}

		// Processing history
		// Header title
		var hist = resp.History;
		tr = new Element('tr');
		td = new Element('td', { colspan: 2, 'class': 'qfits-result-header-title'});
		td.insert('SEx processing history (' + hist.length + ')');
		tr.insert(td);
		tab2.insert(tr);

		tr = new Element('tr');
		td = new Element('td', {colspan: '2'});
		htab = new Element('table', {'class': 'qfits-result-history'});
		td.insert(htab);
		tr.insert(td);
		tab2.insert(tr);
	
		hist.each(function(task) {
			tr = new Element('tr');
			// Emphasis of current history entry
			if (resp.TaskId == task.TaskId)
				tr.setAttribute('class', 'history-current');
	
			// Icon
			td = new Element('td');
			var src = task.Success ? 'success' : 'error';
			var img = new Element('img', {src: '/media/themes/{{ user.get_profile.guistyle }}/img/admin/icon_' + src + '.gif'});
			td.insert(img);
			tr.insert(td);
	
			// Date-time, duration
			td = new Element('td');
			var a = new Element('a', {href: '/youpi/results/' + uidsex + '/' + task.TaskId + '/'});
			a.insert(task.Start + ' (' + task.Duration + ')');
			td.insert(a);
			tr.insert(td);
	
			// Hostname
			tr.insert(new Element('td').update(task.Hostname));
	
			// User
			tr.insert(new Element('td').update(task.User));
	
			// Reprocess option
			td = new Element('td', {'class': 'reprocess'});
			img = new Element('img', {
				onclick: uidsex + ".reprocess_image('" + task.TaskId + "');",
				src: '/media/themes/{{ user.get_profile.guistyle }}/img/misc/reprocess.gif'
			});
			td.insert(img);
			tr.insert(td);
	
			htab.insert(tr);
		});

		// Run parameters
		tr = new Element('tr');
		td = new Element('td');
		td.setAttribute('colspan', '2');
		td.setAttribute('class', 'qfits-result-header-title');
		td.insert('Sex run parameters');
		tr.insert(td);
		tab2.insert(tr);

/*
		//Flag 
		tr = new Element('tr');
		td = new Element('td').insert('Flag path:');
		tr.insert(td);

		td = new Element('td').insert(resp.Flag.length > 0 ? resp.Flag : '--');
		tr.insert(td);
		tab2.insert(tr);

		// Weight
		tr = new Element('tr');
		td = new Element('td').insert('Weight path:');
		tr.insert(td);

		td = new Element('td').insert(resp.Weight.length > 0 ? resp.Weight : '--');
		tr.insert(td);
		tab2.insert(tr);

		// Psf
		tr = new Element('tr');
		td = new Element('td').insert('Psf path:');
		tr.insert(td);

		td = new Element('td').insert(resp.Psf.length > 0 ? resp.Psf : '--');
		tr.insert(td);
		tab2.insert(tr);
*/
		// Output directory
		tr = new Element('tr');
		td = new Element('td', {nowrap: 'nowrap'}).update('Results output dir:');
		tr.insert(td);
	
		td = new Element('td').update(resp.ResultsOutputDir);
		tr.insert(td);
		tab2.insert(tr);
	
		// Config file
		tr = new Element('tr');
		td = new Element('td', {colspan: 2});
		if (resp.Success) {
			td.setAttribute('style', 'border-bottom: 2px #5b80b2 solid');
		}
		var cdiv = new Element('div', {
						id: 'config-' + resp.TaskId,
						'class': 'config_file'
		});
		var pre = new Element('pre').insert(resp.Config);
		cdiv.insert(pre);
		tr.insert(td);
		tab2.insert(tr);

		var confbox = new DropdownBox(td, 'Toggle Sex config file view');
		$(confbox.getContentNode()).insert(cdiv);
	
		// Error log file when failure
		if (!resp['Success']) {
			tr = new Element('tr');
			td = new Element('td', {style: 'border-bottom: 2px #5b80b2 solid',
									colspan: '2'
			});
			var but = new Element('input', {type: 'button',
											value: 'Toggle error log file view',
											onclick: "toggleDisplay('log-" + resp['TaskId'] + "');"
			});
			td.insert(but);
			var cdiv = new Element('div', { id: 'log-' + resp['TaskId'],
											style: 'height: 200px; overflow: auto; background-color: black; padding-left: 5px; display: none'
			});
			var pre = new Element('pre').update(resp['Log']);
			cdiv.insert(pre);
			td.insert(cdiv);
			tr.insert(td);
			tab2.insert(tr);

			return;
		}
	
		d.insert(tab);
		container.insert(d);
	},


	showSavedItems: function() {
		var cdiv = $('plugin_menuitem_sub_' + uidsex).update();
		var div = new Element('div', {'class': 'savedItems', id: uidsex + '_saved_items_div'});
		cdiv.insert(div);
	
		var r = new HttpRequest(
				div.id,
				null,	
				// Custom handler for results
				function(resp) {
					div.update();
	
					var total = resp['result'].length;
					var countNode = $('plugin_' + uidsex + '_saved_count').update();
					var txt;
					
					if (total > 0)
						txt = total + ' item' + (total > 1 ? 's' : '');
					else
						txt = 'No item';
					countNode.update(txt);
	
					var table = new Element('table', {'class': 'savedItems'});
					var tr, th;
					var icon = new Element('img', {	'src': '/media/themes/{{ user.get_profile.guistyle }}/img/32x32/' + uidsex + '.png',
													'style': 'vertical-align:middle; margin-right: 10px;'
					});
	
					tr = new Element('tr');
					th = new Element('th', {'colspan': '8'});
					th.insert(icon);
					th.insert('{{ plugin.description }}: ' + resp['result'].length + ' saved item' + (resp['result'].length > 1 ? 's' : ''));
					tr.insert(th);
					table.insert(tr);
	
					tr = new Element('tr');
					var headers = $A(['Date', 'User', 'Name', '# images', 'Config', 'Paths', 'Action']);
					headers.each(function(header) {
						tr.insert(new Element('th').update(header));
					});
					table.insert(tr);
	
					var delImg, trid;
					var tabi, tabitr, tabitd;
					resp.result.each(function(res, k) {
						console.log(eval(res.idList));
						idList = eval(res.idList);
						trid = uidsex + '_saved_item_' + k + '_tr';
						tr = new Element('tr', {id: trid});

						// Date
						td = new Element('td').update(res.date);
						tr.insert(td);
	
						// User
						td = new Element('td', {'class': 'config'}).update(res.username);
						tr.insert(td);
	
						// Name
						td = new Element('td', {'class': 'name'}).update(res.name);
						tr.insert(td);

						// Images count
						td = new Element('td', {'class': 'imgCount'});
						var sp = new Element('span', {'style': 'font-weight: bold; text-decoration: underline;'});
						sp.update(idList.length > 1 ? 'Batch' : 'Single');
						td.insert(sp).insert(new Element('br'));
						tr.insert(td);
						

						idList.each(function(i) {
							td.insert(i.length).insert(new Element('br'));
						});
						tr.insert(td);

						// Config
						td = new Element('td', {'class': 'config'}).update(res.config);
						tr.insert(td);

						// Handling paths
						td = new Element('td');
						tabi = new Element('table', {'class': 'info'});
						
						// Flag
						tabitr = new Element('tr');
						tabitd = new Element('td', {'class': 'label'});
						tabitd.update('Flag: ');
						tabitr.insert(tabitd);
						tabitd = new Element('td', {'class': 'file'});
						if (res.flagPath.length)
							tabitd.update(reduceString(res.flagPath));
						else
							tabitd.update('Not specified');
						tabitr.insert(tabitd);
						tabi.insert(tabitr);					
						
						// Weight
						tabitr = new Element('tr');
						tabitd = new Element('td', {'class': 'label'});
						tabitd.update('Weight: ');
						tabitr.insert(tabitd);
						tabitd = new Element('td', {'class': 'file'});
						if (res.weightPath.length)
							tabitd.update(reduceString(res.weightPath));
						else
							tabitd.update('Not specified');
						tabitr.insert(tabitd);
						tabi.insert(tabitr);					
						
						// Psf
						tabitr = new Element('tr');
						tabitd = new Element('td', {'class': 'label'});
						tabitd.update('Psf: ');
						tabitr.insert(tabitd);
						tabitd = new Element('td', {'class': 'file'});
						if (res.psfPath.length)
							tabitd.update(reduceString(res.psfPath));
						else
							tabitd.update('Not specified');
						tabitr.insert(tabitd);
						
						tabi.insert(tabitr);
						td.insert(tabi);
						tr.insert(td);
	
						// Delete
						td = new Element('td');
						delImg = new Element('img', {	style: 'margin-right: 5px',
														src: '/media/themes/{{ user.get_profile.guistyle }}/img/misc/delete.gif'
						});
						delImg.c_data = {trid: trid, name: res.name};
						delImg.observe('click', function() {
							{{ plugin.id }}.delSavedItem(this.c_data.trid, this.c_data.name);
						});
						td.insert(delImg);

						var addImg = new Element('img', {	src: '/media/themes/{{ user.get_profile.guistyle }}/img/misc/addtocart_small.gif'
						});
						addImg.c_data = { 	idList: res.idList,
											config: res.config,
											flagPath: res.flagPath,
											weightPath: res.weightPath,
											psfPath: res.psfPath,
											resultsOutputDir: res.resultsOutputDir
						};
						addImg.observe('click', function() {
							{{ plugin.id }}.addToCart(this.c_data);
						});
						td.insert(addImg);

						tr.insert(td);
						table.insert(tr);
					});

					if (resp.result.length) {
						div.insert(table);
					}
					else {
    	                div.insert(icon);
        	            div.insert('  : no saved item');
					}
				}
		);
	
		var post = 	'Plugin=' + uidsex + '&Method=getSavedItems';
		r.send('/youpi/process/plugin/', post);
	},


	delSavedItem: function(trid, name) {
		var r = confirm("Are you sure you want to delete saved item '" + name + "'?");
		if (!r) return;
	
		var trNode = $(trid);
		var reload = false;
	
		var r = new HttpRequest(
				uidsex + '_result',
				null,	
				// Custom handler for results
				function(resp) {
					// 3 = 2 rows of header + 1 row of data
					if (trNode.parentNode.childNodes.length == 3)
						reload = true;
		
					if (reload) 
						window.location.reload();
					else
						trNode.remove();
				}
		);
	
		var post = 	'Plugin=' + uidsex + '&Method=deleteCartItem&Name=' + name;
		r.send('/youpi/process/plugin/', post);
	},


	addToCart: function(data) {
		var p_data = {	plugin_name : uidsex,
						userData :	{ 	'config' 			: data.config,
										'imgList' 			: data.idList,
										'flagPath' 			: data.flagPath,
										'weightPath' 		: data.weightPath,
										'psfPath' 			: data.psfPath,
										'resultsOutputDir' 	: data.resultsOutputDir,
						}
		};
	
		s_cart.addProcessing(p_data,
				// Custom hanlder
				function() {
					window.location.reload();
				}
		);
	},

	selectImages: function() {
		var root = document.getElementById('menuitem_sub_0');
		root.setAttribute('align', 'center');
		// Container of the ImageSelector widget
		var div = document.createElement('div');
		div.setAttribute('id', uidsex + '_results_div');
		div.setAttribute('align', 'center');
		root.appendChild(div);
		{{ plugin.id }}.ims = new ImageSelector(uidsex + '_results_div');
		{{ plugin.id }}.ims.setTableWidget(new AdvancedTable());
	}
};