// Copyright 2019 The Oppia Authors. All Rights Reserved.
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
 * @fileoverview Tests for Capitalize filter for Oppia.
 */

require('filters/string-utility-filters/capitalize.filter.ts');

describe('Testing filters', function() {
  var filterName = 'capitalize';
  beforeEach(angular.mock.module('oppia'));

  it('should have all expected filters', angular.mock.inject(function($filter) {
    expect($filter(filterName)).not.toEqual(null);
  }));

  it('should correctly capitalize strings', angular.mock.inject(
    function($filter) {
      var filter = $filter('capitalize');

      expect(filter('')).toEqual('');
      expect(filter(null)).toEqual(null);
      expect(filter(undefined)).toEqual(undefined);

      expect(filter('a')).toEqual('A');
      expect(filter('a  ')).toEqual('A');
      expect(filter('  a')).toEqual('A');
      expect(filter('  a  ')).toEqual('A');

      expect(filter('a  b ')).toEqual('A  b');
      expect(filter('  a  b ')).toEqual('A  b');
      expect(filter('  ab c ')).toEqual('Ab c');
      expect(filter('  only First lettEr is  Affected ')).toEqual(
        'Only First lettEr is  Affected');
    }
  ));
});
