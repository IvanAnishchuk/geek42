# Copyright 2026 geek42 contributors
# Distributed under the terms of the Creative Commons Zero v1.0 Universal license

EAPI=8

DISTUTILS_USE_PEP517=hatchling
PYTHON_COMPAT=( python3_{13,14} )

inherit distutils-r1

if [[ ${PV} == 9999 ]]; then
	inherit git-r3
	EGIT_REPO_URI="https://github.com/IvanAnishchuk/geek42.git"
else
	inherit pypi
	KEYWORDS="~amd64 ~arm64 ~ppc64 ~riscv ~x86"
fi

DESCRIPTION="Convert GLEP 42 Gentoo news repositories into static blogs"
HOMEPAGE="
	https://github.com/IvanAnishchuk/geek42
	https://pypi.org/project/geek42/
"

LICENSE="CC0-1.0"
SLOT="0"

RDEPEND="
	dev-vcs/git
	app-portage/gemato
	>=dev-python/pydantic-2.0[${PYTHON_USEDEP}]
	>=dev-python/jinja2-3.1[${PYTHON_USEDEP}]
	>=dev-python/typer-0.15[${PYTHON_USEDEP}]
	>=dev-python/rich-13.0[${PYTHON_USEDEP}]
	>=dev-python/markdown-3.5[${PYTHON_USEDEP}]
	>=dev-python/gemato-20[${PYTHON_USEDEP}]
"
BDEPEND="
	test? (
		>=dev-python/pytest-8.0[${PYTHON_USEDEP}]
		dev-python/pytest-cov[${PYTHON_USEDEP}]
	)
"

distutils_enable_tests pytest

python_install_all() {
	local DOCS=( README.md CHANGELOG.md SECURITY.md )
	local HTML_DOCS=( docs/. )
	distutils-r1_python_install_all
}

pkg_postinst() {
	elog "geek42 is installed as an alternative to eselect news."
	elog ""
	elog "To get started:"
	elog "  geek42 init"
	elog "  \$EDITOR geek42.toml   # configure your news sources"
	elog "  geek42 pull"
	elog "  geek42 list"
	elog "  geek42 read-new       # equivalent to 'eselect news read new'"
	elog ""
	elog "See /usr/share/doc/${PF}/ for full documentation."
}
