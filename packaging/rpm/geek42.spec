%global pypi_name geek42
%global _description %{expand:
geek42 converts GLEP 42 news item repositories into a static blog
with RSS/Atom feeds, Markdown exports, and a terminal reader —
without requiring eselect news. It supports multiple sources,
read/unread tracking, compose and revise workflows, and a built-in
news file linter with 15 diagnostic rules.}

Name:           %{pypi_name}
Version:        0.4.0
Release:        1%{?dist}
Summary:        GLEP 42 Gentoo news to static blog converter

License:        CC0-1.0
URL:            https://github.com/IvanAnishchuk/%{pypi_name}
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{pypi_name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel >= 3.13
BuildRequires:  python3-hatchling
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-pytest
BuildRequires:  python3-pytest-cov

Requires:       git

%description %_description

%package -n python3-%{pypi_name}
Summary:        %{summary}
%description -n python3-%{pypi_name} %_description

%prep
%autosetup -n %{pypi_name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files %{pypi_name}

%check
%pytest tests/ -v

%files -n python3-%{pypi_name} -f %{pyproject_files}
%license LICENSE.md
%doc README.md CHANGELOG.md SECURITY.md docs/
%{_bindir}/geek42

%changelog
* Fri Apr 10 2026 Ivan Anishchuk <ivan@agorism.org> - 0.4.0-1
- New upstream release.
- Adds commit/push/sign/verify/deploy-status commands.
- Full newsrepo scaffold with gemato Manifests.

* Fri Apr 10 2026 Ivan Anishchuk <ivan@agorism.org> - 0.3.0-1
- New upstream release.
- Adds --directory / -C option to all commands.

* Thu Apr 09 2026 Ivan Anishchuk <ivan@agorism.org> - 0.2.0-1
- New upstream release.
- Adds compose/revise/read-new commands.
- Full supply-chain security hardening.

* Thu Apr 09 2026 Ivan Anishchuk <ivan@agorism.org> - 0.1.0-1
- Initial release.
