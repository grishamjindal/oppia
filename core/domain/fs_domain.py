# coding: utf-8
#
# Copyright 2016 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Domain objects representing a file system and a file stream."""

import logging

from core.domain import change_domain
from core.platform import models
import feconf
import utils

import cloudstorage

app_identity_services = models.Registry.import_app_identity_services()
(file_models,) = models.Registry.import_models([
    models.NAMES.file
])

CHANGE_LIST_SAVE = [{'cmd': 'save'}]

ALLOWED_ENTITY_NAMES = [
    feconf.ENTITY_TYPE_EXPLORATION, feconf.ENTITY_TYPE_TOPIC,
    feconf.ENTITY_TYPE_SKILL, feconf.ENTITY_TYPE_STORY,
    feconf.ENTITY_TYPE_QUESTION]


class FileMetadataChange(change_domain.BaseChange):
    """Domain object for changes made to a file metadata object."""
    pass


class FileChange(change_domain.BaseChange):
    """Domain object for changes made to a file object."""
    pass


class FileMetadata(object):
    """A class representing the metadata of a file.

    Attributes:
        size: int. The size of the file, in bytes.
    """

    def __init__(self, metadata):
        """Constructs a FileMetadata object.

        Args:
            metadata: FileMetadataModel. The file metadata model instance.
        """
        self._size = metadata.size if (metadata is not None) else None

    @property
    def size(self):
        """Returns the size of the file, in bytes.

        Returns:
            int. The size of the file, in bytes.
        """
        return self._size


class FileStreamWithMetadata(object):
    """A class that wraps a file stream, but adds extra attributes to it.

    Attributes:
        content: str. The content of the file snapshot.
        version: int. The version number of the file.
        metadata: FileMetadata. The file metadata domain instance.
    """

    def __init__(self, content, version, metadata):
        """Constructs a FileStreamWithMetadata object.

        Args:
            content: str. The content of the file snapshots.
            version: int. The version number of the file.
            metadata: FileMetadataModel. The file metadata model instance.
        """
        self._content = content
        self._version = version
        self._metadata = FileMetadata(metadata)

    def read(self):
        """Emulates stream.read(). Returns all bytes and emulates EOF.

        Returns:
            content: str. The content of the file snapshot.
        """
        content = self._content
        self._content = ''
        return content

    @property
    def metadata(self):
        """Returns the file metadata model instance.

        Returns:
            FileMetadataModel. The file metadata model instance.
        """
        return self._metadata

    @property
    def version(self):
        """Returns the version number of the file.

        Returns:
            int. The version number of the file.
        """
        return self._version


class GeneralFileSystem(object):
    """The parent class which is inherited by both DatastoreBackedFileSystem
    and GcsFileSystem as the member variables in both classes are the same.

    Attributes:
        entity_name: str. The name of the entity (eg: exploration, topic etc).
        entity_id: str. The ID of the corresponding entity.
    """

    def __init__(self, entity_name, entity_id):
        """Constructs a GeneralFileSystem object.

        Args:
            entity_name: str. The name of the entity
                (eg: exploration, topic etc).
            entity_id: str. The ID of the corresponding entity.
        """
        self._validate_entity_parameters(entity_name, entity_id)
        self._assets_path = '%s/%s/assets' % (entity_name, entity_id)

    def _validate_entity_parameters(self, entity_name, entity_id):
        """Checks whether the entity_id and entity_name passed in are valid.

        Args:
            entity_name: str. The name of the entity
                (eg: exploration, topic etc).
            entity_id: str. The ID of the corresponding entity.

        Raises:
            ValidationError. When parameters passed in are invalid.
        """
        if entity_name not in ALLOWED_ENTITY_NAMES:
            raise utils.ValidationError(
                'Invalid entity_name received: %s.' % entity_name)
        if not isinstance(entity_id, basestring):
            raise utils.ValidationError(
                'Invalid entity_id received: %s' % entity_id)
        if entity_id == '':
            raise utils.ValidationError('Entity id cannot be empty')

    @property
    def assets_path(self):
        """Returns the path of the parent folder of assets.

        Returns:
            str. The path.
        """
        return self._assets_path


class DatastoreBackedFileSystem(GeneralFileSystem):
    """A datastore-backed read-write file system for a single entity.

    The conceptual intention is for each entity type to have its own parent
    folder. In this, each individual entity will have its own folder with the
    corresponding ID as the folder name. These folders will then have the assets
    folder inside which stores images, audio etc (example path:
    story/story_id/assets/). An asset has no meaning outside its entity, so the
    assets in these asset folders should therefore not be edited directly. They
    should only be modified as side-effects of some other operation on their
    corresponding entity (such as adding an image to that entity).

    In general, assets should be retrieved only within the context of the
    entity that contains them, and should not be retrieved outside this
    context.
    """

    _DEFAULT_VERSION_NUMBER = 1

    def _get_file_metadata(self, filepath, version):
        """Return the desired file metadata.

        Returns None if the file does not exist.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            version: int. The version number of the file whose metadata is to be
                returned.

        Returns:
            FileMetadataModel or None. The model instance representing the file
                metadata with the given assets_path, filepath, and version,
                or None if the file does not exist.
        """
        if version is None:
            return file_models.FileMetadataModel.get_model(
                self._assets_path, filepath)
        else:
            return file_models.FileMetadataModel.get_version(
                self._assets_path, filepath, version)

    def _get_file_data(self, filepath, version):
        """Return the desired file content.

        Returns None if the file does not exist.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            version: int. The version number of the file to be returned.

        Returns:
            FileModel or None. The model instance representing the file with the
                given assets_path, filepath, and version; or None if the file
                does not exist.
        """
        if version is None:
            return file_models.FileModel.get_model(
                self._assets_path, filepath)
        else:
            return file_models.FileModel.get_version(
                self._assets_path, filepath, version)

    def _save_file(self, user_id, filepath, raw_bytes):
        """Create or update a file.

        Args:
            user_id: str. The user_id of the user who wants to create or update
                a file.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            raw_bytes: str. The content to be stored in file.

        Raises:
            Exception: The maximum allowed file size is 1MB.
        """
        if len(raw_bytes) > feconf.MAX_FILE_SIZE_BYTES:
            raise Exception('The maximum allowed file size is 1 MB.')

        metadata = self._get_file_metadata(filepath, None)
        if not metadata:
            metadata = file_models.FileMetadataModel.create(
                self._assets_path, filepath)
        metadata.size = len(raw_bytes)

        data = self._get_file_data(filepath, None)
        if not data:
            data = file_models.FileModel.create(
                self._assets_path, filepath)
        data.content = raw_bytes

        data.commit(user_id, CHANGE_LIST_SAVE)
        metadata.commit(user_id, CHANGE_LIST_SAVE)

    def get(self, filepath, version=None, mode=None):  # pylint: disable=unused-argument
        """Gets a file as an unencoded stream of raw bytes.

        If `version` is not supplied, the latest version is retrieved. If the
        file does not exist, None is returned.

        The 'mode' argument is unused. It is included so that this method
        signature matches that of other file systems.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            version: int or None. The version number of the file. None indicates
                the latest version of the file.
            mode: str. Unused argument.

        Returns:
            FileStreamWithMetadata or None. It returns FileStreamWithMetadata
                domain object if the file exists. Otherwise, it returns None.
        """
        metadata = self._get_file_metadata(filepath, version)
        if metadata:
            data = self._get_file_data(filepath, version)
            if data:
                if version is None:
                    version = data.version
                return FileStreamWithMetadata(data.content, version, metadata)
            else:
                logging.error(
                    'Metadata and data for file %s (version %s) are out of '
                    'sync.' % (filepath, version))
                return None
        else:
            return None

    def commit(self, user_id, filepath, raw_bytes, unused_mimetype):
        """Saves a raw bytestring as a file in the database.

        Args:
            user_id: str. The user_id of the user who wants to create or update
                a file.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            raw_bytes: str. The content to be stored in the file.
            unused_mimetype: str. Unused argument.
        """
        self._save_file(user_id, filepath, raw_bytes)

    def delete(self, user_id, filepath):
        """Marks the current version of a file as deleted.

        Args:
            user_id: str. The user_id of the user who wants to create or update
                a file.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
        """

        metadata = self._get_file_metadata(filepath, None)
        if metadata:
            metadata.delete(user_id, '')

        data = self._get_file_data(filepath, None)
        if data:
            data.delete(user_id, '')

    def isfile(self, filepath):
        """Checks the existence of a file.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.

        Returns:
            bool. Whether the file exists.
        """
        metadata = self._get_file_metadata(filepath, None)
        return bool(metadata)

    def listdir(self, dir_name):
        """Lists all files in a directory.

        Args:
            dir_name: str. The directory whose files should be listed. This
                should not start with '/' or end with '/'.

        Returns:
            list(str). A lexicographically-sorted list of filenames,
                each of which is prefixed with dir_name.
        """
        # The trailing slash is necessary to prevent non-identical directory
        # names with the same prefix from matching, e.g. /abcd/123.png should
        # not match a query for files under /abc/.
        prefix = '%s' % utils.vfs_construct_path(
            '/', self._assets_path, dir_name)
        if not prefix.endswith('/'):
            prefix += '/'

        result = set()
        metadata_models = file_models.FileMetadataModel.get_undeleted()
        for metadata_model in metadata_models:
            filepath = metadata_model.id
            if filepath.startswith(prefix):
                # Because the path is /<entity>/<entity_id>/assets/abc.png.
                result.add('/'.join(filepath.split('/')[4:]))
        return sorted(list(result))


class GcsFileSystem(GeneralFileSystem):
    """Wrapper for a file system based on GCS.

    This implementation ignores versioning.
    """

    def isfile(self, filepath):
        """Checks if the file with the given filepath exists in the GCS.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.

        Returns:
            bool. Whether the file exists in GCS.
        """
        bucket_name = app_identity_services.get_gcs_resource_bucket_name()

        # Upload to GCS bucket with filepath
        # "<bucket>/<entity>/<entity-id>/assets/<filepath>".
        gcs_file_url = (
            '/%s/%s/%s' % (
                bucket_name, self._assets_path, filepath))
        try:
            return bool(cloudstorage.stat(gcs_file_url, retry_params=None))
        except cloudstorage.NotFoundError:
            return False

    def get(self, filepath, version=None, mode=None):  # pylint: disable=unused-argument
        """Gets a file as an unencoded stream of raw bytes.

        If `version` argument is unused. It is included so that this method
        signature matches that of other file systems.

        The 'mode' argument is unused. It is included so that this method
        signature matches that of other file systems.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            version: str. Unused argument.
            mode: str. Unused argument.

        Returns:
            FileStreamWithMetadata or None. It returns FileStreamWithMetadata
                domain object if the file exists. Otherwise, it returns None.
        """
        if self.isfile(filepath):
            bucket_name = app_identity_services.get_gcs_resource_bucket_name()
            gcs_file_url = (
                '/%s/%s/%s' % (
                    bucket_name, self._assets_path, filepath))
            gcs_file = cloudstorage.open(gcs_file_url)
            data = gcs_file.read()
            gcs_file.close()
            return FileStreamWithMetadata(data, None, None)
        else:
            return None

    def commit(self, unused_user_id, filepath, raw_bytes, mimetype):
        """Args:
            unused_user_id: str. Unused argument.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            raw_bytes: str. The content to be stored in the file.
            mimetype: str. The content-type of the cloud file.
        """
        bucket_name = app_identity_services.get_gcs_resource_bucket_name()

        # Upload to GCS bucket with filepath
        # "<bucket>/<entity>/<entity-id>/assets/<filepath>".
        gcs_file_url = (
            '/%s/%s/%s' % (
                bucket_name, self._assets_path, filepath))
        gcs_file = cloudstorage.open(
            gcs_file_url, mode='w', content_type=mimetype)
        gcs_file.write(raw_bytes)
        gcs_file.close()

    def delete(self, user_id, filepath):  # pylint: disable=unused-argument
        """Deletes a file and the metadata associated with it.

        `user_id` argument is unused. It is included so that this method
        signature matches that of other file systems.

        Args:
            user_id: str. The user_id of the user who wants to create or update
                a file.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
        """
        bucket_name = app_identity_services.get_gcs_resource_bucket_name()
        gcs_file_url = (
            '/%s/%s/%s' % (
                bucket_name, self._assets_path, filepath))
        try:
            cloudstorage.delete(gcs_file_url)
        except cloudstorage.NotFoundError:
            raise IOError('Image does not exist: %s' % filepath)


    def listdir(self, dir_name):
        """Lists all files in a directory.

        Args:
            dir_name: str. The directory whose files should be listed. This
                should not start with '/' or end with '/'.

        Returns:
            list(str). A lexicographically-sorted list of filenames.
        """
        if dir_name.endswith('/') or dir_name.startswith('/'):
            raise IOError(
                'The dir_name should not start with / or end with / : %s' % (
                    dir_name))

        # The trailing slash is necessary to prevent non-identical directory
        # names with the same prefix from matching, e.g. /abcd/123.png should
        # not match a query for files under /abc/.
        prefix = '%s' % utils.vfs_construct_path(
            '/', self._assets_path, dir_name)
        if not prefix.endswith('/'):
            prefix += '/'
        # The prefix now ends and starts with '/'.
        bucket_name = app_identity_services.get_gcs_resource_bucket_name()
        # The path entered should be of the form, /bucket_name/prefix.
        path = '/%s%s' % (bucket_name, prefix)
        stats = cloudstorage.listbucket(path)
        files_in_dir = []
        for stat in stats:
            files_in_dir.append(stat.filename)
        return files_in_dir


class AbstractFileSystem(object):
    """Interface for a file system."""

    def __init__(self, impl):
        """Constructs a AbstractFileSystem object."""
        self._impl = impl

    @property
    def impl(self):
        """Returns a AbstractFileSystem object.

        Returns:
            AbstractFileSystem. The AbstractFileSystem object.
        """
        return self._impl

    def _check_filepath(self, filepath):
        """Raises an error if a filepath is invalid.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.

        Raises:
            IOError: Invalid filepath.
        """
        base_dir = utils.vfs_construct_path(
            '/', self.impl.assets_path, 'assets')
        absolute_path = utils.vfs_construct_path(base_dir, filepath)
        normalized_path = utils.vfs_normpath(absolute_path)

        # This check prevents directory traversal.
        if not normalized_path.startswith(base_dir):
            raise IOError('Invalid filepath: %s' % filepath)

    def isfile(self, filepath):
        """Checks if a file exists. Similar to os.path.isfile(...).

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.

        Returns:
            bool. Whether the file exists.
        """
        self._check_filepath(filepath)
        return self._impl.isfile(filepath)

    def open(self, filepath, version=None, mode='r'):
        """Returns a stream with the file content. Similar to open(...).

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            version: int or None. The version number of the file. None indicates
                the latest version of the file.
            mode: str. The mode with which to open the file.

        Returns:
            FileStreamWithMetadata. The file stream domain object.
        """
        self._check_filepath(filepath)
        return self._impl.get(filepath, version=version, mode=mode)

    def get(self, filepath, version=None, mode='r'):
        """Returns a bytestring with the file content, but no metadata.

        Args:
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            version: int or None. The version number of the file. None indicates
                the latest version of the file.
            mode: str. The mode with which to open the file.

        Returns:
            FileStreamWithMetadata. The file stream domain object.

        Raises:
            IOError: The given (or latest) version of this file stream does not
                exist.
        """
        file_stream = self.open(filepath, version=version, mode=mode)
        if file_stream is None:
            raise IOError(
                'File %s (version %s) not found.'
                % (filepath, version if version else 'latest'))
        return file_stream.read()

    def commit(self, user_id, filepath, raw_bytes, mimetype=None):
        """Replaces the contents of the file with the given by test string.

        Args:
            user_id: str. The user_id of the user who wants to create or update
                a file.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
            raw_bytes: str. The content to be stored in the file.
            mimetype: str. The content-type of the file.
        """
        raw_bytes = str(raw_bytes)
        self._check_filepath(filepath)
        self._impl.commit(user_id, filepath, raw_bytes, mimetype)

    def delete(self, user_id, filepath):
        """Deletes a file and the metadata associated with it.

        Args:
            user_id: str. The user_id of the user who wants to create or update
                a file.
            filepath: str. The path to the relevant file within the entity's
                assets folder.
        """
        self._check_filepath(filepath)
        self._impl.delete(user_id, filepath)

    def listdir(self, dir_name):
        """Lists all the files in a directory. Similar to os.listdir(...).

        Args:
            dir_name: str. The directory whose files should be listed. This
                should not start with '/' or end with '/'.

        Returns:
            list(str). A lexicographically-sorted list of filenames,
            each of which is prefixed with dir_name.
        """
        self._check_filepath(dir_name)
        return self._impl.listdir(dir_name)
