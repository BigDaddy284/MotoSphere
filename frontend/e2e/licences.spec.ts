import path from 'node:path'
import { gather, LICENCES_FILE, written } from '../sitebuild/licences.ts'
import { SITE_PATH } from '../site.ts'
import { expect, test } from './fixtures'

/**
 * The site ships code of other people, and their licences go with it: the
 * build writes them into one file of the site. These tests read that file as
 * the built site serves it.
 */

// The folder of the front end, whose packages the site is built from.
const PROJECT = path.resolve(import.meta.dirname, '..')

test.describe('the licences of the packages the site ships', () => {
  test('are served as plain text, under the path of the site', async ({ request }) => {
    const response = await request.get(LICENCES_FILE)

    expect(response.status()).toBe(200)
    expect(new URL(response.url()).pathname).toBe(`${SITE_PATH}licences.txt`)
    expect(response.headers()['content-type']).toMatch(/^text\/plain\b/)
  })

  test('are not at the root of the server', async ({ request }) => {
    const response = await request.get(`/${LICENCES_FILE}`, { maxRedirects: 0 })

    expect(response.status()).toBe(404)
  })

  test('are those of the packages installed, as the build step writes them', async ({
    request,
  }) => {
    const response = await request.get(LICENCES_FILE)

    expect(await response.text()).toBe(written(gather(PROJECT)))
  })

  test('name React with the words of its licence', async ({ request }) => {
    const text = await (await request.get(LICENCES_FILE)).text()
    const react = gather(PROJECT).find(({ name }) => name === 'react')

    expect(react).toBeDefined()
    expect(text).toContain(`\nreact ${react?.version}\nLicence: MIT\n`)
    expect(text).toContain('Permission is hereby granted, free of charge')
  })

  test('are named in the source of the page', async ({ request }) => {
    const page = await (await request.get('./')).text()

    expect(page).toContain(
      `<!-- The licences of the packages this site is built with are in ${LICENCES_FILE}, beside this page. -->`,
    )
  })
})
