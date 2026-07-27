/*
 * Copyright 2026 Vesper contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

package org.thoughtcrime.securesms.recipients

import org.signal.core.models.ServiceId.ACI
import java.security.MessageDigest
import java.util.Locale

/**
 * Computes the stable identifier used by Vesper's config service.
 */
internal fun hashVesperAci(aci: ACI): String {
  return MessageDigest
    .getInstance("SHA-256")
    .digest(aci.toString().lowercase(Locale.ROOT).toByteArray(Charsets.UTF_8))
    .joinToString(separator = "") { byte -> "%02x".format(byte.toInt() and 0xff) }
}
