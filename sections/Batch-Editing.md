---
layout: docs_page
title: Batch Editing
navbar_active_tab: docs
previous_doc_filename: Customizing-Export.html
previous_doc_title: Customizing Export
next_doc_filename: Known-Issues.html
next_doc_title: Known Issues
---

Batch Editing
-------------

Need to edit layers directly in the image without exporting them?
Export Layers allows you to do just that.
Simply press the `Settings` button and select `Batch Editing`.

The dialog now only displays the procedures and constraints applied to layers:

![Dialog of Export Layers with batch editing enabled](../images/screenshot_dialog_batch_editing.png)

Export-related settings such as filename pattern, file extension and output folder are hidden as they are not applicable for batch editing.

It is highly recommended to uncheck `Use layer size` as the entire image would be resized to the last layer processed.

If the `Layers` constraint is unchecked - meaning that layer groups are also processed - the layer groups will be copied and inserted as regular layers to work around the fact that some procedures cannot be applied on layer groups (e.g. `gimp-drawable-brightness-contrast`).

Note that if both `Batch Editing` and `Show More Settings` are checked and you uncheck `Show More Settings`, then `Batch Editing` is also unchecked since the left side of the dialog would be completely empty.
