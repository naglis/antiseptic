===============================
antiseptic
===============================

.. image:: https://img.shields.io/pypi/v/antiseptic.svg?style=flat
    :target: https://pypi.python.org/pypi/antiseptic/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/antiseptic.svg?style=flat
    :target: https://pypi.python.org/pypi/antiseptic/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/travis/naglis/antiseptic/master.png?style=flat
    :target: https://travis-ci.org/naglis/antiseptic
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/naglis/antiseptic/master.svg?style=flat
    :target: https://coveralls.io/r/naglis/antiseptic?branch=master
    :alt: Test coverage

.. image:: http://img.shields.io/pypi/l/antiseptic.svg?style=flat
    :alt: GPL2 License

A simple command-line movie directory name cleaner

The pitch
---------
Before:

::

    $ tree MOVIES/ -L 1
    MOVIES/
    ├── Across.the.Hall.2009.DVDRip.XviD-BeStDivX
    ├── A.Mighty.Heart[2007[DvDrip[Eng]-aXXo
    ├── District.9.REPACK.R5.LiNE.XviD-KAMERA
    ├── Drag Me To Hell 2009.DvDRip-FxM
    ├── Dragonball.Evolution.DVDRip.XviD-DoNE
    ├── Ed.Wood.XviD.DVD-Rip
    ├── Gamer.2009.WORKPRiNT.XviD.AC3-ViSiON
    ├── G-Force.DVDRip.XviD-JUMANJi
    ├── Ghosts Of Girlfriends Past.2009.WorkPrint.Xvid {1337x}-Noir
    ├── G.I.Joe The Rise Of Cobra.2009.DvDRip-FxM
    ├── Harry Potter and the Half Blood Prince.DVDRip.XviD-NeDiVx
    ├── I.Served.the.King.of.England.DVDRip.XviD-iAPULA
    ├── Knowing (2009) [DvdRip] [Xvid] {1337x}-Noir
    ├── Star.Trek.2009.DvDRip-FxM
    ├── State of Play (2009) DVDRip XviD
    ├── The.Hangover.[2009].DVDSCR.[ENG]-MAXSPEED
    ├── The.Hurt.Locker.2008.DVDRiP.XViD
    ├── Transformers.Revenge.of.the.Fallen.DVDRip.XviD-iMBT
    └── UP[2009]DvDrip-LW

After:

::

    $ tree MOVIES/ -L 1
    MOVIES/
    ├── Across the Hall (2009)
    ├── A Mighty Heart (2007)
    ├── District 9
    ├── Drag Me To Hell (2009)
    ├── Dragonball Evolution
    ├── Ed Wood
    ├── Gamer (2009)
    ├── G-Force
    ├── Ghosts Of Girlfriends Past (2009)
    ├── G I Joe The Rise Of Cobra (2009)
    ├── Harry Potter and the Half Blood Prince
    ├── I Served the King of England
    ├── Knowing (2009)
    ├── Star Trek (2009)
    ├── State of Play (2009)
    ├── The Hangover. (2009)
    ├── The Hurt Locker (2008)
    ├── Transformers Revenge of the Fallen
    └── UP (2009)

Features
--------

* Uses regex rules
* Command line interface
* No third party dependencies
* Easily updateable rules
* No online services

Requirements
------------

* Python 3

Getting started
---------------

::

    $ pip install antiseptic
    $ antiseptic update
    $ antiseptic rename <movie_directory>

If you have many movies inside one directory and want to rename all of them at
once, use the ``-d``, ``--dir`` flag:

::

    $ antiseptic rename -d <movie_directory>

How to update the rules?
========================

::

    $ antiseptic update
