/*
 * Class: TagPanel
 * Handles tags
 *
 * For convenience, private data member names (both variables and functions) start with an underscore.
 *
 * Constructor Parameters:
 *
 * container - string or DOM object: name of parent DOM block container
 *
 */
function TagPanel(container) {
	// Group: Constants
	// -----------------------------------------------------------------------------------------------------------------------------


	/*
	 * Var: _container
	 * DOM container
	 *
	 */
	var _container = null;
	/*
	 * Var: _infoDiv
	 * DOM div displaying info messages
	 *
	 */
	var _infoDiv = null;
	/*
	 * Var: _editDiv
	 * DOM div displaying tag edition form
	 *
	 */
	var _editDiv = null;
	/*
	 * Var: _id
	 * Tag panel id
	 *
	 */
	var _id = 'tag_panel_';


	// Group: Variables
	// -----------------------------------------------------------------------------------------------------------------------------


	/*
	 * Var: _tags
	 * Available tags
	 *
	 */
	var _tags = new Array();



	// Group: Functions
	// -----------------------------------------------------------------------------------------------------------------------------
	

	/*
	 * Function: _showEditForm
	 * Show edition form
	 *
	 */ 
	function _showEditForm() {
		var f = new Element('form', {'class': 'tagform'});
		var tab = new Element('table');
		var tr, td, lab, inp;

		// Preview
		tr = new Element('tr');
		td = new Element('td');
		lab = new Element('label').update('Preview:');
		td.insert(lab);
		tr.insert(td);

		td = new Element('td');
		tr.insert(td);
		tab.insert(tr);

		// Tag name
		tr = new Element('tr');
		td = new Element('td');
		lab = new Element('label').update('Tag name:');
		td.insert(lab);
		tr.insert(td);

		td = new Element('td');
		inp = new Element('input', {id: _id + 'tag_name_input'});
		td.insert(inp);
		tr.insert(td);
		tab.insert(tr);

		// Comment
		tr = new Element('tr');
		td = new Element('td');
		lab = new Element('label').update('Comment:');
		td.insert(lab);
		tr.insert(td);

		td = new Element('td');
		inp = new Element('input');
		td.insert(inp);
		tr.insert(td);
		tab.insert(tr);

		// Style
		tr = new Element('tr');
		td = new Element('td');
		lab = new Element('label').update('Style:');
		td.insert(lab);
		tr.insert(td);

		td = new Element('td').update('stylepicker');
		tr.insert(td);
		tab.insert(tr);

		// Buttons
		tr = new Element('tr');
		td = new Element('td', {colspan: 2}).setStyle({textAlign: 'right'});
		var addb = new Element('input', {type: 'button', value: 'Add!'});
		var cancelb = new Element('input', {type: 'button', value: 'Cancel', style: 'margin-right: 10px'});
		cancelb.observe('click', function() {
			_editDiv.slideUp();
			$(_id + 'add_new_span').appear();
		});
		td.insert(cancelb);
		td.insert(addb);
		tr.insert(td);
		tab.insert(tr);

		f.insert(tab);
		_editDiv.insert(f);
		_editDiv.slideDown({afterFinish: function() {
			$(_id + 'tag_name_input').focus();
		} });
	}


	/*
	 * Function: _checkForTags
	 * Fetches any tag information from DB then updates the UI
	 *
	 */ 
	function _checkForTags() {
		var r = new HttpRequest(
			_infoDiv,
			null,	
			// Custom handler for results
			function(r) {
				_infoDiv.update();
				if (!r.tags.length) {
					_infoDiv.update('No tags have been created so far. ');
					var s = new Element('span', {id: _id + 'add_new_span'}).update('Please ');
					var l = new Element('a', {href: '#'}).update('add a new tag');
					l.observe('click', function() {
						s.fade();
						_editDiv.update();
						_showEditForm();
					});
					s.insert(l).insert('.');
					_infoDiv.insert(s);
				}
			}
		);
	
		r.send('/youpi/tags/fetchtags/');
	}

	/*
	 * Function: _render
	 * Main rendering function
	 *
	 */ 
	function _render() {
		_container = $(container);
		if (!container) {
			throw "Please supply a valid DOM container!";
			return;
		}

		_infoDiv = new Element('div');
		_editDiv = new Element('div').setStyle({marginTop: '10px'}).hide();
		_container.insert(_infoDiv).insert(_editDiv);

		_checkForTags();
	}

	_render();
}
