# Oenskeskyen Batch Upload

## Extracting .webloc files from Safari

To extract bookmarks from Safari as .webloc files:

1. Open Safari and go to your bookmarks (Bookmarks > Show Bookmarks or Cmd+Option+B)
2. Select the bookmarks you want to export
3. Drag the selected bookmarks to a folder in Finder
4. Safari will create .webloc files for each bookmark

## Extracting URLs from .webloc files

Once you have the .webloc files in a folder, use the extraction script:

```bash
./scripts/extract_urls.sh <folder_path>
```

This will create an `wishes.txt` file with all the extracted URLs.
