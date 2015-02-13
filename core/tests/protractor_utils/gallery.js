// Copyright 2014 The Oppia Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @fileoverview Utilities for the gallery in end-to-end tests with protractor.
 *
 * @author Jacob Davis (jacobdavis11@gmail.com)
 */

var editor = require('./editor.js');
var forms = require('./forms.js');

var setLanguages = function(languages) {
  forms.AutocompleteMultiDropdownEditor(
    element(by.css('.protractor-test-gallery-language-selector'))
  ).setValues(languages);
};

var expectCurrentLanguageSelectionToBe = function(expectedLanguages) {
  forms.AutocompleteMultiDropdownEditor(
    element(by.css('.protractor-test-gallery-language-selector'))
  ).expectCurrentSelectionToBe(expectedLanguages);
};

// Here section is expected to be 'category'. The label can be any category.
// Verifies the previous state of the checkbox, then clicks it.
var _clickCheckbox = function(section, label, isPreviouslyTicked) {
  element.all(by.css('.protractor-test-gallery-' + section)).
      map(function(option) {
    return option.getText().then(function(text) {
      if (text === label) {
        var checkbox =
          option.element(by.css('.protractor-test-gallery-checkbox'));
        if (isPreviouslyTicked) {
          expect(checkbox.isSelected()).toBeTruthy();
        } else {
          expect(checkbox.isSelected()).toBeFalsy();
        }
        checkbox.click();
        return true;
      }
      return false;
    });
  }).then(function(results) {
    var foundCheckbox = false;
    for (var i = 0; i < results.length; i++) {
      foundCheckbox = foundCheckbox || results[i];
    }
    if (!foundCheckbox) {
      throw Error('Checkbox ' + label + ' not found in section ' + section);
    }
  });
};

var tickCheckbox = function(section, label) {
  _clickCheckbox(section, label, false);
};

var untickCheckbox = function(section, label) {
  _clickCheckbox(section, label, true);
};

// Returns a promise of all explorations with the given name.
var _getExplorationElements = function(name) {
  return element.all(by.css('.protractor-test-gallery-tile')).filter(
      function(tile, index) {
    return tile.element(by.css('.protractor-test-gallery-tile-title')).
        getText().then(function(tileTitle) {
      return (tileTitle === name);
    });
  });
};

var expectExplorationToBeVisible = function(name) {
  _getExplorationElements(name).then(function(elems) {
    expect(elems.length).not.toBe(0);
  });
};

var expectExplorationToBeHidden = function(name) {
  _getExplorationElements(name).then(function(elems) {
    expect(elems.length).toBe(0);
  });
};

var playExploration = function(name) {
  _getExplorationElements(name).then(function(elems) {
    elems[0].element(by.css('.protractor-test-gallery-tile-title')).click();
  });
};

var editExploration = function(name) {
  _getExplorationElements(name).then(function(elems) {
    elems[0].element(by.css('.protractor-test-edit-exploration')).click();
  });
  editor.exitTutorialIfNecessary();
};

var getExplorationObjective = function(name) {
  return _getExplorationElements(name).then(function(elems) {
    return elems[0].element(by.css('.protractor-test-exploration-objective')).
      getText();
  });
};

exports.setLanguages = setLanguages;
exports.expectCurrentLanguageSelectionToBe = expectCurrentLanguageSelectionToBe;
exports.tickCheckbox = tickCheckbox;
exports.untickCheckbox = untickCheckbox;
exports.expectExplorationToBeVisible = expectExplorationToBeVisible;
exports.expectExplorationToBeHidden = expectExplorationToBeHidden;
exports.playExploration = playExploration;
exports.editExploration = editExploration;
exports.getExplorationObjective = getExplorationObjective;