/*
 * Copyright 2026 Molly Instant Messenger
 * SPDX-License-Identifier: AGPL-3.0-only
 */

import org.w3c.dom.Document
import org.w3c.dom.Element
import javax.xml.parsers.DocumentBuilderFactory
import javax.xml.transform.TransformerFactory
import javax.xml.transform.dom.DOMSource
import javax.xml.transform.stream.StreamResult

/** Reads and writes Android XML resources. */
private object XmlRes {
  fun parseStrings(stringsFile: File): Pair<Document, List<Element>> {
    val doc = parseXmlFile(stringsFile)
    val strings = doc.getElements("string") + doc.getElements("plurals")
    return doc to strings
  }

  fun parseColors(resFile: File): Pair<Document, Map<String, String>> {
    val doc = parseXmlFile(resFile)
    val colors = doc
      .getElements("color")
      .associateBy(
        { it.getAttribute("name") },
        { it.firstChild.nodeValue }
      )
    return doc to colors
  }

  fun writeToFile(doc: Document, file: File) {
    val transformer = TransformerFactory.newInstance().newTransformer()
    transformer.transform(DOMSource(doc), StreamResult(file))
  }

  private fun parseXmlFile(file: File): Document {
    val docBuilder = DocumentBuilderFactory.newInstance().newDocumentBuilder()
    return docBuilder.parse(file).apply {
      xmlStandalone = true
    }
  }

  private fun Document.getElements(tagName: String) =
    getElementsByTagName(tagName).let { nodes ->
      (0 until nodes.length).map { nodes.item(it) as Element }
    }
}


/**
 * Replaces Signal references with Vesper in translation files.
 * The resource names are read from Vesper's standalone manifest so upstream's hottest
 * strings.xml file does not need downstream-only attributes.
 */
tasks.register("updateTranslationsAll") {
  group = "Vesper"
  description = "Updates translations in all modules."

  subprojects.forEach { module ->
    val baseStringsFile = module.file("src/main/res/values/strings.xml")
    if (baseStringsFile.exists()) {
      val subtask = module.registerTranslationsTask(baseStringsFile)
      dependsOn(subtask)
    }
  }
}

private fun Project.registerTranslationsTask(baseStringsFile: File): TaskProvider<Task> {
  val baseFileProvider = provider { baseStringsFile }
  val stringManifestProvider = provider {
    rootProject.file(".vesper/strings-manifest.txt")
  }
  val translationFilesProvider = provider {
    fileTree("src/main/res") {
      include("**/values-*/strings.xml")
    }
  }
  val rootDirProvider = provider { rootProject.rootDir }

  val task = tasks.register("updateTranslations") {
    group = "Vesper"
    description = "Replaces 'Signal' with 'Vesper' in translation files."

    inputs.file(baseFileProvider)
      .withPropertyName("baseStringsFile")
      .withPathSensitivity(PathSensitivity.RELATIVE)

    inputs.file(stringManifestProvider)
      .withPropertyName("stringManifest")
      .withPathSensitivity(PathSensitivity.RELATIVE)

    inputs.files(translationFilesProvider)
      .withPropertyName("translationFiles")
      .withPathSensitivity(PathSensitivity.RELATIVE)

    outputs.files(translationFilesProvider)

    doLast {
      val baseStringsFile = baseFileProvider.get()
      val translationFiles = translationFilesProvider.get()
      val rootDir = rootDirProvider.get()

      val vesperifyList = stringManifestProvider.get()
        .readLines()
        .map { it.trim() }
        .filter { it.isNotEmpty() && !it.startsWith("#") }
        .toSet()

      if (vesperifyList.isNotEmpty() && translationFiles.isEmpty) {
        logger.error("No translation files found in src/main/res/values-*/")
      }

      fun replaceSignalRefs(elem: Element): Boolean {
        val oldContent = elem.textContent
        elem.textContent = elem.textContent
          .replace("Signal", "Vesper")
        return oldContent != elem.textContent
      }

      fun processTranslationFile(stringsFile: File): Boolean {
        val (xmlDoc, translatedStrings) = XmlRes.parseStrings(stringsFile)
        var updated = false

        translatedStrings.forEach { elem ->
          val name = elem.getAttribute("name")
          if (name in vesperifyList) {
            when (elem.tagName) {
              "string" -> {
                if (replaceSignalRefs(elem)) updated = true
              }

              "plurals" -> {
                val items = elem.getElementsByTagName("item")
                for (i in 0 until items.length) {
                  val item = items.item(i) as Element
                  if (replaceSignalRefs(item)) updated = true
                }
              }
            }
          }
        }

        // Leave untouched files alone so their timestamps stay stable.
        if (updated) {
          XmlRes.writeToFile(xmlDoc, stringsFile)
        }
        return updated
      }

      translationFiles.files.parallelStream().forEach {
        if (processTranslationFile(it)) {
          logger.lifecycle(
            "Updated translations in: " + it.toRelativeString(rootDir)
          )
        }
      }
    }
  }
  return task
}

/**
 * Replaces Signal brand colours with Vesper colours.
 *
 * Reads colour definitions from "core:ui/src/main/res/values/vesper_colors.xml" and replaces
 * each "stock_*" hex value with its "vesper_*" counterpart
 * in XML, Kotlin, and Java source files.
 */
tasks.register("updateColors") {
  group = "Vesper"
  description = "Replaces Signal colours with Vesper colours in the app source set."

  val colorsFileProvider = provider {
    project(":core:ui").file("src/main/res/values/vesper_colors.xml")
  }
  val sourceFilesProvider = colorsFileProvider.map { colorsFile ->
    objects.fileCollection().apply {
      subprojects.forEach { module ->
        val srcDir = module.file("src/main")
        from(fileTree(srcDir) {
          include("**/*.xml", "**/*.kt", "**/*.java")
          exclude("res/values*/strings*.xml")
          exclude(colorsFile.relativeTo(srcDir).path)
        })
      }
    }.asFileTree
  }
  val rootDirProvider = provider { rootProject.rootDir }

  inputs.file(colorsFileProvider)
    .withPropertyName("colorsFile")
    .withPathSensitivity(PathSensitivity.RELATIVE)

  outputs.files(sourceFilesProvider)

  doLast {
    val colorsFile = colorsFileProvider.get()
    val sourceFiles = sourceFilesProvider.get()
    val rootDir = rootDirProvider.get()

    val (_, colors) = XmlRes.parseColors(colorsFile)

    // Map each stock_* colour to its vesper_* counterpart.
    val colorMappings = colors.keys
      .filter { it.startsWith("stock_") }
      .map { stockName ->
        val vesperName = stockName.replaceFirst("stock_", "vesper_")
        val stockValue = colors.getValue(stockName).removePrefix("#").uppercase()
        val vesperValue = colors[vesperName]?.removePrefix("#")?.uppercase()
          ?: throw GradleException("Missing '$vesperName' for '$stockName' in '$colorsFile'")
        stockValue to vesperValue
      }.toSet()

    // A colour cannot be both a source and a different target.
    val stockToVesper = colorMappings.groupBy({ it.first }, { it.second })
    val vesperToStock = colorMappings.groupBy({ it.second }, { it.first })

    val stockConflicts = stockToVesper.filterValues { it.size > 1 }
    val vesperConflicts = vesperToStock.filterValues { it.size > 1 }

    val cycles = vesperToStock.keys.intersect(stockToVesper.keys).filterNot { color ->
      color in stockToVesper[color].orEmpty() && color in vesperToStock[color].orEmpty()
    }

    if (stockConflicts.isNotEmpty() || vesperConflicts.isNotEmpty() || cycles.isNotEmpty()) {
      val message = buildString {
        appendLine("Some colours map to more than one value:")
        stockConflicts.forEach { (color, set) ->
          appendLine("Signal #$color → Vesper: ${set.map { "#$it" }}")
        }
        vesperConflicts.forEach { (color, set) ->
          appendLine("Vesper #$color ← Signal: ${set.map { "#$it" }}")
        }
        cycles.forEach { color ->
          appendLine("Signal ↔ Vesper: #$color")
        }
      }.trim()
      logger.error(message)
      throw GradleException("Conflicting colour mappings found in '$colorsFile'")
    }

    val regexReplacements = colorMappings.map { (stockHex, vesperHex) ->
      // Groups: (1) prefix, (2) alpha and (3) hex colour.
      val regex = """(?i)(0x|#)([0-9A-Fa-f]{2})?($stockHex)\b""".toRegex()
      regex to vesperHex
    }

    var anyChanges = false

    sourceFiles.files.parallelStream().forEach { file ->
      val content = file.readText()
      var modified = content
      var changes = 0

      regexReplacements.forEach { (regex, newHex) ->
        modified = regex.replace(modified) { match ->
          val (_, prefix, alpha, oldHex) = match.groupValues
          if (!oldHex.equals(newHex, ignoreCase = true)) {
            changes++
            "$prefix$alpha$newHex"
          } else match.value
        }
      }

      if (changes > 0) {
        file.writeText(modified)
        logger.lifecycle(
          "Updated: ${file.toRelativeString(rootDir)}: $changes change(s)"
        )
        anyChanges = true
      }
    }

    logger.lifecycle(
      if (anyChanges) "Updated Signal colours to Vesper."
      else "The colours are already up to date."
    )
  }
}
