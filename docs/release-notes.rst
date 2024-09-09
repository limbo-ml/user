.. _release-notes:

Release Notes
=============

Limbo 0.4.0 - September 9, 2024
-------------------------------

* Added an option to compress annotation metadata by removing bboxes, contours, and redundant categories.
* Raise an error when passing the wrong number of arguments to limbo-compress --mask.
* limbo-compress generates empty masks for data without cryptomattes.
* Added documentation for 3D model data, along with links to external 3D resources.

Limbo 0.3.1 - November 6, 2023
------------------------------

* Fix problems with the documentation build.

Limbo 0.3.0 - November 6, 2023
------------------------------

* Documented additional camera metadata that can be acessed directly from images.
* Added an article on object detection to the user guide.
* Added the `limbo-compress` command for optimizing data acess.
* General code and documentation cleanup.

Limbo 0.2.0 - November 21, 2022
-------------------------------

* Completed one million synthetic images!
* limbo-stats generates additional statistics, including license and copyright information.
* Categories can contain slashes.
* Added the limbo-lint command for cleaning datasets.
* Switched to pyproject.toml and flit for packaging.
* Greatly improved install documentation.

Limbo 0.1.0 - November 16, 2021
-------------------------------

* Initial Release.
