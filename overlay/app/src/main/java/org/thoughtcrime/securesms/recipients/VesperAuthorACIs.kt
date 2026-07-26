/*
 * Copyright 2026 Vesper contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

package org.thoughtcrime.securesms.recipients

import org.signal.core.models.ServiceId.ACI

/**
 * Account identifiers that receive Vesper's author badge.
 *
 * This owned overlay is the source of truth so the identities remain separate
 * from upstream-facing feature patches.
 */
internal val vesperAuthorACIs: Set<ACI> = setOf(
  ACI.parseOrThrow("1520bdf1-0a44-469d-bf9d-46b66b178041")
)
