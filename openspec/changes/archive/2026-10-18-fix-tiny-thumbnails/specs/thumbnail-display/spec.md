# Thumbnail display

## Purpose

Governs how page thumbnails are painted in the thumbnail panel, so that the
sharp previews produced by thumbnail generation actually reach the screen at
their generated size.

## ADDED Requirements

### Requirement: Thumbnails are painted at their generated size

The thumbnail panel SHALL paint each page's thumbnail at the size at which it
was generated (at most the configured thumbnail size in each dimension). The
panel SHALL NOT scale the thumbnail down to a toolkit or stylesheet icon size
when painting it.

#### Scenario: Painting a full-size thumbnail in the panel

- **WHEN** a page thumbnail is displayed in the thumbnail panel
- **THEN** the painted thumbnail SHALL be as large as the generated thumbnail
  pixbuf, preserving its aspect ratio
- **AND** a thumbnail generated at the configured thumbnail size (100 px) with
  an aspect ratio taller than the panel row SHALL paint 100 px wide and 65 px
  high for a 100x65 page

#### Scenario: Toolkit icon-size defaults do not shrink thumbnails

- **WHEN** the widget toolkit applies a default stylesheet icon size
  (e.g. `-gtk-icon-size: 16px` on the renderer's style class)
- **THEN** the thumbnail panel SHALL NOT paint the thumbnail smaller than the
  generated thumbnail size on account of that default
