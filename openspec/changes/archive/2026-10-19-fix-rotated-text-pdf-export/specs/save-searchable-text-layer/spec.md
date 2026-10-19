## ADDED Requirements

### Requirement: Rotated text is rendered at its text angle
When scantpaper saves a PDF, every word whose effective text angle is not
horizontal SHALL be rendered in the output PDF at that angle. The effective
angle is the word's own text angle combined with the angles of all of its
ancestors, taken once each.

A word SHALL be rendered at its own angle whether it sits directly under a
page, inside a synthetic line created during export, or inside an existing
line whose angle differs. When one line contains words with different
effective angles, export SHALL separate them so each angle is represented
correctly in the saved text layer.

The set and order of extracted words SHALL be unaffected by rotation.

#### Scenario: A manually rotated word is saved vertically
- **WHEN** the user adds a word, rotates it 90 degrees, and saves the page as
  a searchable PDF
- **THEN** the word in the output PDF SHALL be rendered vertically
- **AND** its text SHALL remain extractable
- **AND** its rendered position SHALL sit inside the slice's saved bounding
  box rather than spilling down the page

#### Scenario: A rotated word inside an unrotated OCR line is saved vertically
- **WHEN** a word with a 90-degree text angle is nested in an existing OCR
  line whose text angle is 0
- **AND** the page is saved as a searchable PDF
- **THEN** the rotated word SHALL be rendered vertically in the output PDF
- **AND** the other words on that line SHALL remain horizontal

#### Scenario: Ancestor rotation is applied exactly once
- **WHEN** a word inherits a 90-degree rotation from an ancestor and carries
  no additional rotation of its own
- **AND** the page is saved as a searchable PDF
- **THEN** the word SHALL be rendered 90 degrees from horizontal in the output
  PDF
- **AND** the rotation SHALL NOT be applied twice

#### Scenario: Unrotated text is unchanged
- **WHEN** a page whose words all have an effective angle of 0 is saved as a
  searchable PDF
- **THEN** every word SHALL be rendered horizontally as before
- **AND** the extracted word set and order SHALL be unchanged
